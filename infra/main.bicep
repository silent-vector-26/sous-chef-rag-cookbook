targetScope = 'resourceGroup'

@description('Prefix for resource names')
param environmentName string
param location string = resourceGroup().location
@description('Container image; azd replaces this on deploy')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

var token = toLower(uniqueString(resourceGroup().id, environmentName))

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

// ---- Azure OpenAI (chat + embeddings), Entra-only ----
resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'aoai-${token}'
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: { customSubDomainName: 'aoai-${token}', disableLocalAuth: true, publicNetworkAccess: 'Enabled' }
}

resource chatModel 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-4o-mini'
  sku: { name: 'GlobalStandard', capacity: 30 }
  properties: { model: { format: 'OpenAI', name: 'gpt-4o-mini', version: '2024-07-18' } }
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
  location: location
  sku: { name: 'basic' }
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
  location: location
  kind: 'ContentSafety'
  sku: { name: 'S0' }
  properties: { customSubDomainName: 'cs-${token}', disableLocalAuth: true }
}

// ---- Hosting: Container Apps with system-assigned managed identity ----
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

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-sous-chef-${token}'
  location: location
  tags: { 'azd-service-name': 'web' }
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: env.id
    configuration: { ingress: { external: true, targetPort: 8501 } }
    template: {
      containers: [{
        name: 'web'
        image: containerImage
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'BACKEND', value: 'azure' }
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

// ---- RBAC for the app identity (no keys anywhere) ----
var roles = {
  openaiUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
  searchData: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
  searchSvc: '7ca78c08-252a-4471-8644-bb5ff32d4ba0' // Search Service Contributor
  csUser: 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User
}

resource raOpenai 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: openai
  name: guid(openai.id, app.id, roles.openaiUser)
  properties: { principalId: app.identity.principalId, principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.openaiUser) }
}

resource raSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, app.id, roles.searchData)
  properties: { principalId: app.identity.principalId, principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchData) }
}

resource raSearchSvc 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, app.id, roles.searchSvc)
  properties: { principalId: app.identity.principalId, principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchSvc) }
}

resource raSafety 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: safety
  name: guid(safety.id, app.id, roles.csUser)
  properties: { principalId: app.identity.principalId, principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.csUser) }
}

output AZURE_OPENAI_ENDPOINT string = openai.properties.endpoint
output AZURE_SEARCH_ENDPOINT string = 'https://${search.name}.search.windows.net'
output AZURE_CONTENT_SAFETY_ENDPOINT string = safety.properties.endpoint
output APP_URL string = 'https://${app.properties.configuration.ingress.fqdn}'
