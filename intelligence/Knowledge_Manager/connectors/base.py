from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FileRecord:
    rel_path: str
    abs_path: str
    file_type: str = ""
    checksum: str = ""
    file_size: int = 0
    mtime: float = 0


class ConnectionBase(ABC):
    def __init__(self, connection_id: str, config: dict):
        self.connection_id = connection_id
        self.config = config

    @abstractmethod
    def list_files(self) -> List[FileRecord]:
        ...

    @abstractmethod
    def read_file(self, rel_path: str) -> Optional[str]:
        ...

    def read_file_bytes(self, rel_path: str) -> Optional[bytes]:
        """Đọc file dưới dạng nhị phân (bytes). Các subclass nên override phương thức này thưa Master."""
        content_str = self.read_file(rel_path)
        if content_str is not None:
            return content_str.encode("utf-8", errors="replace")
        return None

    @abstractmethod
    def get_metadata(self, rel_path: str) -> dict:
        ...

    def watch(self):
        return None
