from dataclasses import dataclass
from typing import Tuple
from memory.memory_zones import MemoryZone

@dataclass(frozen=True)
class MemoryCapability:
    """Quyền truy xuất vùng nhớ (ACL)"""
    read_zones: Tuple[MemoryZone, ...]
    write_zones: Tuple[MemoryZone, ...]

class MemoryACLManager:
    """Quản trị viên phân quyền Memory"""
    
    # Pre-defined profiles
    PLANNER_PROFILE = MemoryCapability(
        read_zones=(MemoryZone.WORKING, MemoryZone.SYSTEM, MemoryZone.LONG_TERM),
        write_zones=() # Planner tuyệt đối KHÔNG được ghi trực tiếp
    )
    
    EXECUTOR_PROFILE = MemoryCapability(
        read_zones=(MemoryZone.WORKING,),
        write_zones=(MemoryZone.WORKING,) # Tool chỉ ghi output tạm thời
    )
    
    RUNTIME_PROFILE = MemoryCapability(
        read_zones=(MemoryZone.WORKING, MemoryZone.EPISODIC, MemoryZone.LONG_TERM, MemoryZone.SECURITY, MemoryZone.SYSTEM),
        write_zones=(MemoryZone.WORKING, MemoryZone.EPISODIC, MemoryZone.LONG_TERM)
    )

    def check_access(self, capability: MemoryCapability, zone: MemoryZone, action: str) -> bool:
        if action.upper() == "READ":
            return zone in capability.read_zones
        elif action.upper() == "WRITE":
            return zone in capability.write_zones
        return False
