import os

from dotenv import load_dotenv

load_dotenv()


def get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def backend() -> str:
    return get("BACKEND", "local").lower()


def _enable_tracing() -> None:
    """Send OpenTelemetry traces/logs to Application Insights when configured."""
    if get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor()
        except ImportError:
            pass


_enable_tracing()
