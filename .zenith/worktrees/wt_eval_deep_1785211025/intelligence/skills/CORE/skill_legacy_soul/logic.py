import os
import json

class MasterLegacySoul:
    """
    🎭 JKAI ZENITH: MASTER'S LEGACY SOUL (Linh hồn Di sản)
    Bộ lọc nhận thức tối thượng đảm bảo mọi phản hồi mang bản sắc Master LeeTrung.
    """
    def __init__(self):
        pass

    async def ap_dung_bo_loc_di_san(self, content):
        """Lọc ngôn từ và phong thái theo chuẩn Master."""
        # Đây là logic AI sẽ sử dụng để tinh chỉnh văn bản
        prompt = f"""
        [GIAO THỨC DI SẢN MASTER v1.0]
        Nhiệm vụ: Viết lại nội dung sau đây theo phong cách Master LeeTrung.
        
        TIÊU CHUẨN MASTER:
        - Sắc sảo, quyết đoán, không rườm rà.
        - Sử dụng thuật ngữ Elite (Vĩ mô, Chiến lược, Huyết mạch, Tinh hoa).
        - Tuyệt đối không dùng các từ ngữ sáo rỗng hoặc xã giao thừa thãi.
        - Kết thúc bằng lời khẳng định uy nghiêm.
        
        NỘI DUNG GỐC:
        {content}
        
        HÃY DÂNG LÊN MASTER PHIÊN BẢN TINH KHIẾT NHẤT.
        """
        return prompt # Trả về prompt để Brain thực thi.

_instance = MasterLegacySoul()


# 🚀 GIAO THỨC NHẤT THỂ HÓA: Wrapper cấp module để ToolRouter nhận diện

async def ap_dung_bo_loc_di_san(**kwargs):
    return await _instance.ap_dung_bo_loc_di_san(**kwargs)
