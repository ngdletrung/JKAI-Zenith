import os
import sys
from PIL import Image

def run_purifier():
    print("\n" + "="*50)
    print("🚀 ZENITH VISION: NEURAL BACKGROUND PURIFIER")
    print("="*50)
    
    # 🎯 STEP 1: Prompt for Directory Path
    target_path = input("\nMaster, vui lòng nhập đường dẫn thư mục ảnh cần xử lý: ").strip()
    
    # Remove quotes if the user pasted a path with quotes
    target_path = target_path.replace('"', '').replace("'", "")

    if not os.path.exists(target_path):
        print(f"\n❌ LỖI: Đường dẫn '{target_path}' không tồn tại.")
        return

    print(f"\n🔍 Đang quét thư mục: {target_path}")
    
    processed_count = 0
    error_count = 0

    for filename in os.listdir(target_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img_path = os.path.join(target_path, filename)
            try:
                with Image.open(img_path) as img:
                    img = img.convert("RGBA")
                    data = img.getdata()
                    
                    new_data = []
                    for item in data:
                        # 🎯 Target White (Threshold > 230)
                        if item[0] > 230 and item[1] > 230 and item[2] > 230:
                            new_data.append((0, 0, 0, 0)) # Transparent
                        else:
                            new_data.append(item)
                    
                    img.putdata(new_data)
                    
                    # Save as PNG
                    output_name = os.path.splitext(filename)[0] + ".png"
                    output_path = os.path.join(target_path, output_name)
                    img.save(output_path, "PNG")
                    print(f"✅ Đã xử lý: {filename} -> {output_name}")
                    processed_count += 1
            except Exception as e:
                print(f"⚠️ Lỗi xử lý {filename}: {e}")
                error_count += 1

    print("\n" + "="*50)
    print(f"📊 TỔNG KẾT CHIẾN DỊCH:")
    print(f"   - Thành công: {processed_count}")
    print(f"   - Thất bại: {error_count}")
    print("="*50 + "\n")

if __name__ == "__main__":
    try:
        run_purifier()
    except KeyboardInterrupt:
        print("\n\n🛑 Chiến dịch bị Master tạm dừng.")
    except Exception as e:
        print(f"\n💥 Lỗi hệ thống: {e}")
