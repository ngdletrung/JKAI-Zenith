from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SourceType(str, Enum):
    INTELLIGENCE_DIR = "intelligence_dir"
    LOCAL_FOLDER = "local_folder"
    WEB_URL = "web_url"
    ONEDRIVE = "onedrive"
    GOOGLE_DRIVE = "gdrive"
    SHAREPOINT = "sharepoint"
    DROPBOX = "dropbox"
    CUSTOM_PLUGIN = "custom_plugin"


@dataclass
class Source:
    id: str
    name: str
    type: SourceType
    config: dict = field(default_factory=dict)
    enabled: bool = True
    target_collection: str = "jkai_external"


@dataclass
class FileRecord:
    source_id: str
    rel_path: str
    abs_path: Optional[str] = None
    file_type: Optional[str] = None
    checksum: Optional[str] = None
    file_size: int = 0
    mtime: float = 0.0
    status: str = "pending"
