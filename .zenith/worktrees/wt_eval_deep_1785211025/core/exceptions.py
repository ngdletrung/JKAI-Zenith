class AIJKGlobalException(Exception):
    """Base exception class for JKAI v6."""
    pass

class ConfigurationError(AIJKGlobalException):
    pass

class DataModelValidationError(AIJKGlobalException):
    pass

class InfrastructureConnectionError(AIJKGlobalException):
    pass