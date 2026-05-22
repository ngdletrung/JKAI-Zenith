"""
⛏️ JKAI ZENITH - KẺ ĐÀO VÀNG DỮ LIỆU (SMART DATASET MINER)
Chuyên dùng để trích xuất tinh hoa từ các kho báu Dataset khổng lồ mà không làm nổ ổ cứng thưa Master.

Công nghệ: 
- HuggingFace Datasets `streaming=True` (Chỉ tải từng dòng, không tải toàn bộ file).
- Nén thành JSONL cực nhẹ.
"""

import os
import json
import logging
from typing import Optional

try:
    from datasets import load_dataset
except ImportError:
    print("Vui lòng cài đặt: pip install datasets")
    exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MINER")

DATASET_DIR = r"D:\Docker\N8N\intelligence\datasets"
os.makedirs(DATASET_DIR, exist_ok=True)

def mine_dataset(
    repo_id: str, 
    split: str = "train", 
    max_rows: int = 5000, 
    output_name: Optional[str] = None,
    subset: Optional[str] = None
):
    """
    Hút tinh hoa từ Dataset.
    :param repo_id: Tên repo trên HuggingFace (VD: 'tatsu-lab/alpaca')
    :param max_rows: Số dòng tinh hoa muốn hút về.
    """
    output_name = output_name or repo_id.split("/")[-1]
    output_path = os.path.join(DATASET_DIR, f"{output_name}_mined_{max_rows}.jsonl")
    
    logger.info(f"⛏️ Đang đào kho báu: {repo_id} (Subset: {subset})")
    logger.info(f"💾 Sẽ lưu tại: {output_path}")
    
    try:
        # ⚡ STREAMING MODE: Đỉnh cao tiết kiệm dung lượng
        dataset = load_dataset(repo_id, name=subset, split=split, streaming=True)
        
        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for row in dataset:
                if count >= max_rows:
                    break
                
                # Làm sạch dữ liệu, chỉ lấy những cột quan trọng nếu có
                clean_row = {k: v for k, v in row.items() if isinstance(v, (str, int, float, bool))}
                
                f.write(json.dumps(clean_row, ensure_ascii=False) + "\n")
                count += 1
                
                if count % 1000 == 0:
                    logger.info(f"💎 Đã hút được {count}/{max_rows} dòng tinh hoa...")
                    
        logger.info(f"✅ Hoàn tất! Đã lưu {count} dòng vào {output_path}")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi đào kho báu {repo_id}: {e}")

if __name__ == "__main__":
    print("="*50)
    print("⛏️ JKAI ZENITH - SMART DATASET MINER ONLINE")
    print("="*50)
    
    # 1. Hút thử nghiệm Alpaca (52K -> lấy 2000 dòng chất lượng cao nhất)
    # mine_dataset("tatsu-lab/alpaca", max_rows=2000)
    
    # 2. Hút dữ liệu Tiếng Việt chất lượng cao (Vietnamese Instruction)
    # mine_dataset("hiieu/medqa-vn", max_rows=1000)
    
    print("\n💡 Hướng dẫn:")
    print("Hãy mở file này và thay đổi tham số `repo_id` để hút bộ dữ liệu Ngài muốn thưa Master!")
