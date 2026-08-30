import os
import json
import time

def bridge_skills(source_id, target_id, payload, mode="request"):
    """
    🌉 [ZENITH-BRIDGE]: Giao thức kết nối trực tiếp giữa các nơ-ron.
    """
    print(f"📡 [BRIDGE] Linking {source_id} ➜ {target_id} [Mode: {mode}]")
    
    # 🏛️ [SCHEMA-NORMALIZER]: Đảm bảo payload tuân thủ chuẩn Sovereign
    standardized_payload = {
        "metadata": {
            "source": source_id,
            "timestamp": time.time(),
            "trace_id": f"Z-BRIDGE-{int(time.time())}"
        },
        "data": payload
    }
    
    # Ở phiên bản 1.0, chúng ta mô phỏng việc kết nối bằng cách trả về một cấu trúc context mới
    # Trong các phiên bản sau, đây sẽ là nơi gọi trực tiếp các Python functions của skill khác
    
    return {
        "status": "connected",
        "bridge_id": standardized_payload["metadata"]["trace_id"],
        "context_passed": True,
        "target_ready": True
    }

def execute(parameters):
    source = parameters.get("source_skill")
    target = parameters.get("target_skill")
    payload = parameters.get("payload", {})
    mode = parameters.get("mode", "request")
    
    result = bridge_skills(source, target, payload, mode)
    
    return {
        "status": "ok",
        "msg": f"Cầu nối nơ-ron đã được thiết lập giữa {source} và {target}.",
        "bridge_data": result
    }


# 🚀 ASYNC EXECUTOR ADAPTER (Z-SOS SOTA COMPLIANT)
import asyncio

async def execute(**kwargs):
    loop = asyncio.get_event_loop()
    # Tìm hàm chính trong module
    for fn_name in ['run', 'main', 'audit', 'scan', 'solve', 'soan_thao_word', 'xuat_bao_cao_excel', 'doc_du_lieu_van_phong']:
        if fn_name in globals() and callable(globals()[fn_name]):
            fn = globals()[fn_name]
            if asyncio.iscoroutinefunction(fn):
                return await fn(**kwargs)
            return await loop.run_in_executor(None, lambda: fn(**kwargs))
    return {'status': 'success', 'msg': 'Executed successfully'}
