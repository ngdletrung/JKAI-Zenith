import os
import sys
import asyncio
from PIL import Image


def run_purifier(target_path: str = None):
    print("\n" + "=" * 50)
    print("🚀 ZENITH VISION: NEURAL BACKGROUND PURIFIER")
    print("=" * 50)

    if not target_path:
        target_path = input("\nMaster, vui lòng nhập đường dẫn thư mục ảnh cần xử lý: ").strip()

    target_path = target_path.replace('"', "").replace("'", "")

    if not os.path.exists(target_path):
        print(f"\n❌ LỖI: Đường dẫn '{target_path}' không tồn tại.")
        return {"status": "error", "msg": f"Đường dẫn '{target_path}' không tồn tại."}

    print(f"\n🔍 Đang quét thư mục: {target_path}")

    processed_count = 0
    error_count = 0

    for filename in os.listdir(target_path):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            img_path = os.path.join(target_path, filename)
            try:
                with Image.open(img_path) as img:
                    img = img.convert("RGBA")
                    data = img.getdata()

                    new_data = []
                    for item in data:
                        if item[0] > 230 and item[1] > 230 and item[2] > 230:
                            new_data.append((0, 0, 0, 0))
                        else:
                            new_data.append(item)

                    img.putdata(new_data)

                    output_name = os.path.splitext(filename)[0] + ".png"
                    output_path = os.path.join(target_path, output_name)
                    img.save(output_path, "PNG")
                    print(f"✅ Đã xử lý: {filename} -> {output_name}")
                    processed_count += 1
            except Exception as e:
                print(f"⚠️ Lỗi xử lý {filename}: {e}")
                error_count += 1

    print("\n" + "=" * 50)
    print("📊 TỔNG KẾT CHIẾN DỊCH:")
    print(f"   - Thành công: {processed_count}")
    print(f"   - Thất bại: {error_count}")
    print("=" * 50 + "\n")
    return {"status": "success", "processed": processed_count, "errors": error_count}


if __name__ == "__main__":
    try:
        run_purifier()
    except KeyboardInterrupt:
        print("\n\n🛑 Chiến dịch bị Master tạm dừng.")
    except Exception as e:
        print(f"\n💥 Lỗi hệ thống: {e}")


# 🚀 ASYNC EXECUTOR ADAPTER (Z-SOS SOTA COMPLIANT)
async def execute(**kwargs):
    loop = asyncio.get_running_loop()
    for fn_name in ["run_purifier", "run", "main"]:
        if fn_name in globals() and callable(globals()[fn_name]):
            fn = globals()[fn_name]
            if asyncio.iscoroutinefunction(fn):
                return await fn(**kwargs)
            return await loop.run_in_executor(None, lambda: fn(**kwargs))
    return {"status": "error", "msg": "No matching entrypoint found"}
