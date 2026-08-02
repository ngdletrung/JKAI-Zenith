from .base import ConnectionBase, FileRecord
from .local import LocalFileConnector
from .web import WebConnector

__all__ = ["ConnectionBase", "FileRecord", "LocalFileConnector", "WebConnector"]
