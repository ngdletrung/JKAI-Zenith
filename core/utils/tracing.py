import logging
import os

logger = logging.getLogger("jkai.core.tracing")

# Jaeger da bi xoa khoi docker-compose.
# Giu lai init_tracing lam no-op de tranh loi import o cac file khac.

def init_tracing(service_name: str, app=None):
    return None
