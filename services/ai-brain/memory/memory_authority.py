# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/memory/memory_authority.py
# - Role: Ultimate Memory Guard (Sovereign Memory)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v18.0
# [WORKING PRINCIPLES]:
# - Tuan thu nghiem ngat No-Emoji va Zero-Noise.
# - Tich hop thuc te voi Redis va Qdrant client de phan vung bo nho vat ly.
# - Su dung Hybrid Logical Clock (HLC) de phan giai xung dot (Conflict Resolution) chuan xac.

import json
import time
from typing import Optional, Dict, Any
from memory.memory_zones import MemoryZone
from memory.acl_manager import MemoryCapability, MemoryACLManager
from redis_client import get_redis
from semantic_memory import memory as qdrant_memory

class MemoryAuthority:
    """
    Quyen Luc Bo Nho Tuyet Doi (The Ultimate Memory Guard)
    Quyet dinh Consistency, phan giai xung dot (Arbitration), chong Poisoning.
    """
    def __init__(self, acl_manager: MemoryACLManager):
        self.acl_manager = acl_manager
        
    def _parse_hlc(self, hlc_str: str) -> tuple:
        """Tach chuoi HLC thanh (physical_ms, logical_counter)."""
        try:
            parts = hlc_str.split(":")
            phys = int(parts[0])
            log = int(parts[1]) if len(parts) > 1 else 0
            return phys, log
        except Exception:
            return int(time.time() * 1000), 0

    def _compare_hlc(self, hlc1: str, hlc2: str) -> int:
        """So sanh hai HLC. Tra ve 1 neu hlc1 > hlc2, -1 neu hlc1 < hlc2, 0 neu bang nhau."""
        p1, l1 = self._parse_hlc(hlc1)
        p2, l2 = self._parse_hlc(hlc2)
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
        if l1 > l2:
            return 1
        elif l1 < l2:
            return -1
        return 0

    def generate_hlc(self, current_hlc: Optional[str] = None) -> str:
        """Tu dong sinh hoac tang tien Hybrid Logical Clock."""
        now_ms = int(time.time() * 1000)
        if not current_hlc:
            return f"{now_ms}:0"
        
        phys, log = self._parse_hlc(current_hlc)
        if now_ms > phys:
            return f"{now_ms}:0"
        else:
            return f"{phys}:{log + 1}"

    async def commit(self, zone: MemoryZone, payload: dict, capability: MemoryCapability, trace_id: str) -> dict:
        """Chi MemoryAuthority moi co quyen Commit."""
        if not self.acl_manager.check_access(capability, zone, "WRITE"):
            raise PermissionError(f"[MEMORY-VIOLATION]: Trace {trace_id} attempted unauthorized write to {zone.name}")
            
        r = get_redis()
        new_hlc = payload.get("hlc") or self.generate_hlc()
        
        # 1. PHAN GIAI XUNG DOT (Conflict Resolution) & PERSISTENCE CHO REDIS ZONES
        if zone in [MemoryZone.WORKING, MemoryZone.EPISODIC, MemoryZone.SECURITY, MemoryZone.SYSTEM]:
            redis_key = f"memory:{zone.name.lower()}:{trace_id}"
            
            # Doc du lieu hien tai de giai quyet xung dot
            try:
                existing_data_raw = r.get(redis_key)
            except Exception as re_err:
                print(f"[MEMORY-WARN]: Redis read failed: {re_err}")
                existing_data_raw = None
                
            if existing_data_raw:
                try:
                    existing_data = json.loads(existing_data_raw)
                    existing_hlc = existing_data.get("hlc", "0:0")
                    
                    # Neu HLC cu lon hon hoac bang HLC moi, tu choi ghi de (Last-Write-Wins bao ve)
                    if self._compare_hlc(existing_hlc, new_hlc) >= 0:
                        print(f"[MEMORY-CONFLICT]: Conflict detected for key '{redis_key}'. Local HLC '{existing_hlc}' >= Incoming HLC '{new_hlc}'. Write discarded.")
                        return {"status": "conflict_discarded", "reason": "HLC is outdated", "zone": zone.name}
                except Exception as e:
                    print(f"[MEMORY-WARN]: Failed to parse existing data for conflict resolution: {e}")

            # Chuan bi du lieu ghi vao
            envelope = {
                "hlc": new_hlc,
                "payload": payload.get("data", payload),
                "committed_at": time.time(),
                "trace_id": trace_id
            }
            envelope_str = json.dumps(envelope)
            
            # Ghi du lieu voi TTL tuong ung
            try:
                if zone == MemoryZone.WORKING:
                    r.setex(redis_key, 1800, envelope_str)
                else:
                    r.set(redis_key, envelope_str)
            except Exception as wr_err:
                print(f"[MEMORY-ERR]: Redis write failed: {wr_err}")
                return {"status": "error", "reason": str(wr_err), "zone": zone.name}
                
        # 2. PERSISTENCE CHO QDRANT (LONG_TERM) ZONE
        elif zone == MemoryZone.LONG_TERM:
            msg_text = payload.get("text") or json.dumps(payload.get("data", payload))
            tag = payload.get("tag", "KNOWLEDGE")
            try:
                await qdrant_memory.store_log(task_id=trace_id, tag=tag, msg=msg_text)
            except Exception as q_err:
                print(f"[MEMORY-ERR]: Qdrant write failed: {q_err}")
                return {"status": "error", "reason": str(q_err), "zone": zone.name}
            
        return {"status": "committed", "zone": zone.name, "hlc": new_hlc}

    async def read(self, zone: MemoryZone, query: dict, capability: MemoryCapability, trace_id: str) -> dict:
        if not self.acl_manager.check_access(capability, zone, "READ"):
            raise PermissionError(f"[MEMORY-VIOLATION]: Trace {trace_id} attempted unauthorized read from {zone.name}")
            
        r = get_redis()
        
        if zone in [MemoryZone.WORKING, MemoryZone.EPISODIC, MemoryZone.SECURITY, MemoryZone.SYSTEM]:
            redis_key = f"memory:{zone.name.lower()}:{trace_id}"
            try:
                data_raw = r.get(redis_key)
            except Exception as re_err:
                print(f"[MEMORY-ERR]: Redis read failed: {re_err}")
                return {"status": "error", "data": None}
                
            if data_raw:
                try:
                    envelope = json.loads(data_raw)
                    return {"status": "success", "data": envelope.get("payload"), "hlc": envelope.get("hlc")}
                except Exception:
                    return {"status": "success", "raw_data": data_raw}
            return {"status": "empty", "data": None}
            
        elif zone == MemoryZone.LONG_TERM:
            search_query = query.get("text", "")
            limit = query.get("limit", 5)
            if search_query:
                try:
                    results = await qdrant_memory.search(search_query, limit=limit)
                    return {"status": "success", "data": results}
                except Exception as q_err:
                    print(f"[MEMORY-ERR]: Qdrant search failed: {q_err}")
                    return {"status": "error", "data": []}
            return {"status": "empty", "data": []}
            
        return {"status": "unsupported_zone", "data": None}
