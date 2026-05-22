import sys
import os
import time

# Thêm đường dẫn thưa Master
sys.path.append(os.getcwd())

from hlc import hlc, compare_hlc

def test_hlc_monotonicity():
    print("🛡️ [TEST]: Kiểm tra tính đơn điệu của HLC...")
    t1 = hlc.now()
    t2 = hlc.now()
    t3 = hlc.now()
    
    print(f"T1: {t1}")
    print(f"T2: {t2}")
    print(f"T3: {t3}")
    
    assert compare_hlc(t1, t2) < 0
    assert compare_hlc(t2, t3) < 0
    print("✅ [SUCCESS]: HLC luôn tiến về phía trước thưa Master.")

def test_hlc_logical_increment():
    print("\n🛡️ [TEST]: Kiểm tra bước nhảy logic khi wall clock đứng yên...")
    # Giả lập wall clock đứng yên (bằng cách gọi cực nhanh)
    t1 = hlc.now()
    t2 = hlc.now()
    
    if t1.physical_ms == t2.physical_ms:
        print(f"Logical bump detected: {t1.logical} -> {t2.logical}")
        assert t2.logical == t1.logical + 1
        print("✅ [SUCCESS]: Bước nhảy logic chính xác thưa Master.")
    else:
        print("ℹ️ [INFO]: Wall clock tiến quá nhanh, không test được logical bump thô.")

def test_hlc_from_str():
    print("\n🛡️ [TEST]: Kiểm tra giải mã HLC từ chuỗi...")
    from hlc import HlcTimestamp
    t_str = "1716314810000:5:node-test"
    t = HlcTimestamp.from_str(t_str)
    assert t.physical_ms == 1716314810000
    assert t.logical == 5
    assert t.node_id == "node-test"
    assert str(t) == t_str
    print("✅ [SUCCESS]: Giải mã chuỗi HLC chính xác thưa Master.")

if __name__ == "__main__":
    test_hlc_monotonicity()
    test_hlc_logical_increment()
    test_hlc_from_str()
