---
type: python_file
file: exceptions.py
tags: []
---

# exceptions

class AIJKGlobalException(Exception):
    """Base exception class for JKAI v6."""
    pass

class ConfigurationError(AIJKGlobalException):
    pass

class DataModelValidationError(AIJKGlobalException):
    pass

class InfrastructureConnectionError(AIJKGlobalException):
    pass


## Linked by
- [[__init__.py]]
