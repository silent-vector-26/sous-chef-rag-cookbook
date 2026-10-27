targetScope = 'resourceGroup'

@description('Environment name, used in resource names')
param environmentName string
param location string = resourceGroup().location
@description('Entra object id of the deploying user; gets data-plane roles for local ingestion. Empty to skip.')
param principalId string = ''
@description('Container image; azd replaces this on deploy')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
@description('Region for Azure OpenAI / Content Safety (model availability)')
param aiLocation string = location
@description('Region for Azure AI Search (capacity varies by region)')
param searchLocation string = location
@description('Azure AI Search SKU. "free" costs nothing (50 MB, 3 indexes, shared capacity, one per subscription).')
@allowed(['free', 'basic'])
param searchSku string = 'free'

var token = toLower(uniqueString(resourceGroup().id, environmentName))

// ---- Identity (user-assigned so AcrPull exists before the app is created) ----
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${token}'
  location: location
}

// ---- Observability ----
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${token}'
  location: location
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${token}'
  location: location
  kind: 'web'
  properties: { Application_Type: 'web', WorkspaceResourceId: logs.id }
}

// ---- Container registry (no admin user; pulled via managed identity) ----
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'cr${token}'
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

// ---- Azure OpenAI (chat + embeddings), Entra-only ----
resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'aoai-${token}'
  location: aiLocation
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: { customSubDomainName: 'aoai-${token}', disableLocalAuth: true, publicNetworkAccess: 'Enabled' }
}

resource chatModel 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-5.4-mini'
  sku: { name: 'GlobalStandard', capacity: 30 }
  properties: { model: { format: 'OpenAI', name: 'gpt-5.4-mini', version: '2026-03-17' } }
}

resource embedModel 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'text-embedding-3-small'
  dependsOn: [chatModel]
  sku: { name: 'Standard', capacity: 30 }
  properties: { model: { format: 'OpenAI', name: 'text-embedding-3-small', version: '1' } }
}

// ---- Azure AI Search (hybrid + semantic ranker, Entra-only) ----
resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: 'srch-${token}'
  location: searchLocation
  sku: { name: searchSku }
  properties: {
    semanticSearch: 'free'
    disableLocalAuth: true
    replicaCount: 1
    partitionCount: 1
  }
}

// ---- Content Safety (Prompt Shields + harm categories) ----
resource safety 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'cs-${token}'
  location: aiLocation
  kind: 'ContentSafety'
  sku: { name: 'S0' }
  properties: { customSubDomainName: 'cs-${token}', disableLocalAuth: true }
}

// ---- Hosting: Container Apps ----
resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${token}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: logs.properties.customerId, sharedKey: logs.listKeys().primarySharedKey }
    }
  }
}

var roles = {
  openaiUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
  searchData: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
  searchSvc: '7ca78c08-252a-4471-8644-bb5ff32d4ba0' // Search Service Contributor
  csUser: 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull
}

resource raAcr 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, identity.id, roles.acrPull)
  properties: { principalId: identity.properties.principalId, principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.acrPull) }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-sous-chef-${token}'
  location: location
  tags: { 'azd-service-name': 'web' }
  dependsOn: [raAcr]
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: true, targetPort: 8501 }
      registries: [{ server: acr.properties.loginServer, identity: identity.id }]
    }
    template: {
      containers: [{
        name: 'web'
        image: containerImage
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'BACKEND', value: 'azure' }
          { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          { name: 'AZURE_OPENAI_ENDPOINT', value: openai.properties.endpoint }
          { name: 'AZURE_OPENAI_CHAT_DEPLOYMENT', value: chatModel.name }
          { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: embedModel.name }
          { name: 'AZURE_SEARCH_ENDPOINT', value: 'https://${search.name}.search.windows.net' }
          { name: 'AZURE_SEARCH_INDEX', value: 'recipes' }
          { name: 'AZURE_CONTENT_SAFETY_ENDPOINT', value: safety.properties.endpoint }
          { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
        ]
      }]
      scale: { minReplicas: 0, maxReplicas: 2 }
    }
  }
}

// ---- RBAC: app identity (and optionally the deploying user) — no keys anywhere ----
var appId = identity.properties.principalId

resource raOpenai 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: openai
  name: guid(openai.id, identity.id, roles.openaiUser)
  properties: { principalId: appId, principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.openaiUser) }
}

resource raSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, identity.id, roles.searchData)
  properties: { principalId: appId, principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchData) }
}

resource raSearchSvc 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, identity.id, roles.searchSvc)
  properties: { principalId: appId, principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchSvc) }
}

resource raSafety 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: safety
  name: guid(safety.id, identity.id, roles.csUser)
  properties: { principalId: appId, principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.csUser) }
}

// Deploying user: data-plane access so `python -m ingest.index_azure` works locally
resource uOpenai 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: openai
  name: guid(openai.id, principalId, roles.openaiUser)
  properties: { principalId: principalId, principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.openaiUser) }
}

resource uSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: search
  name: guid(search.id, principalId, roles.searchData)
  properties: { principalId: principalId, principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchData) }
}

resource uSearchSvc 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: search
  name: guid(search.id, principalId, roles.searchSvc)
  properties: { principalId: principalId, principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchSvc) }
}

resource uSafety 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: safety
  name: guid(safety.id, principalId, roles.csUser)
  properties: { principalId: principalId, principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.csUser) }
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.properties.loginServer
output AZURE_OPENAI_ENDPOINT string = openai.properties.endpoint
output AZURE_OPENAI_CHAT_DEPLOYMENT string = chatModel.name
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = embedModel.name
output AZURE_SEARCH_ENDPOINT string = 'https://${search.name}.search.windows.net'
output AZURE_SEARCH_INDEX string = 'recipes'
output AZURE_CONTENT_SAFETY_ENDPOINT string = safety.properties.endpoint
output APPLICATIONINSIGHTS_CONNECTION_STRING string = appInsights.properties.ConnectionString
output APP_URL string = 'https://${app.properties.configuration.ingress.fqdn}'
