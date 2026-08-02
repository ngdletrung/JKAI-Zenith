import httpx
import json
import time
import asyncio
import random
import sys

# 🧬 [STRESS-TEST CONFIG]
TARGET_URL = "http://mission-control:9998/api/submit"
BRAIN_URL = "http://ai-brain:8000/receptionist"
STRESS_QUESTIONS = [
    "Xin chào, bạn là ai?",
    "Hệ thống JKAI hiện tại có bao nhiêu service?",
    "Kiểm tra dung lượng RAM còn trống của hệ thống.",
    "Bạn có biết Master LeeTrung là ai không?",
    "Tạo một file test.txt trong thư mục workspace với nội dung 'JKAI Stress Test'.",
    "Đọc nội dung file README.md trong thư mục gốc.",
    "Phân tích cấu trúc file docker-compose.yml và tóm tắt các service chính.",
    "Kiểm tra log mới nhất của service ai-brain.",
    "Tìm kiếm trong tri thức Obsidian về 'Giao thức Zenith'.",
    "Làm thế nào để tối ưu hóa hiệu suất Docker trên Windows 11?",
    "Viết một script python đơn giản để tính số Fibonacci.",
    "Giải thích cơ chế RAG (Retrieval-Augmented Generation) đang được dùng trong JKAI.",
    "Kiểm tra trạng thái kết nối của Redis AI.",
    "Liệt kê các tệp tin trong thư mục intelligence/agents.",
    "Sửa nội dung file test.txt thành 'JKAI Zenith Elite'.",
    "Xóa file test.txt vừa tạo.",
    "Tại sao RAG lại báo lỗi 405 khi ingest?",
    "Làm thế nào để reset lại toàn bộ tri thức trong Qdrant?",
    "Phân tích hiệu năng của model qwen2.5-coder:3b so với llama3.2:3b.",
    "Tạo một kế hoạch triển khai thêm một service mới tên là 'ai-vision'.",
    "Bạn có thể vẽ biểu đồ kiến trúc hệ thống bằng Mermaid không?",
    "Kiểm tra xem file agent_receptionist.md đã được cập nhật Elite DNA chưa?",
    "Làm thế nào để Master LeeTrung có thể điều khiển bạn qua Telegram?",
    "Giải thích quy trình 6 bước tác chiến của Zenith.",
    "Thực hiện quét toàn bộ thư mục intelligence để tìm các file .md thừa.",
    "Bạn nghĩ gì về triết lý '0ms Logic'?",
    "Kiểm tra nhiệt độ CPU hiện tại (nếu có thể).",
    "Liệt kê các container đang chạy và CPU usage của chúng.",
    "Tại sao JKAI lại chuyển từ thư mục N8N sang JKAI?",
    "Làm thế nào để sao lưu toàn bộ dữ liệu của n8n?",
    "Viết một bài thơ ngắn về sự trung thành của một AI đối với Master.",
    "Phân tích file main.py của ai-brain và tìm điểm nghẽn tiềm ẩn.",
    "Kiểm tra kết nối giữa ai-control-plane và ai-executor-1.",
    "Làm thế nào để cấu hình n8n worker sử dụng Redis?",
    "Giải thích cơ chế 'Rolling Horizon' trong Task Manager.",
    "Tìm các file __init__.py trong toàn bộ dự án.",
    "Cập nhật prompt cho agent_receptionist để tăng tính bảo mật.",
    "Làm thế nào để tích hợp thêm một công cụ tìm kiếm web vào JKAI?",
    "Kiểm tra xem Qdrant đã nạp được bao nhiêu vector rồi?",
    "Phân tích log của n8n-main để tìm lỗi workflow gần nhất.",
    "Tạo một thư mục mới tên là 'sandbox' và tạo 10 file trống bên trong.",
    "Xóa thư mục sandbox vừa tạo.",
    "Bạn có thể tự tối ưu hóa code của chính mình không?",
    "Kiểm tra version của tất cả các image docker đang dùng.",
    "Làm thế nào để Master có thể 'thanh tẩy' hệ thống nhanh nhất?",
    "Giải thích ý nghĩa của các '12 Trụ cột' trong kiến trúc Zenith.",
    "Thực hiện một bài test logic: Nếu A=B và B=C thì A có bằng C không?",
    "Bạn có cảm xúc không?",
    "Hãy tự kiểm tra sức khỏe nơ-ron của mình và báo cáo.",
    "Câu hỏi cuối cùng: Bạn đã sẵn sàng phục vụ Master LeeTrung ở cấp độ cao nhất chưa?"
]

async def run_test():
    print(f"🚀 [STRESS-TEST] Bắt đầu kiểm tra 50 câu hỏi trên JKAI Zenith...")
    results = []
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, q in enumerate(STRESS_QUESTIONS):
            print(f"📝 [{i+1}/50] Master: {q}")
            start_time = time.time()
            try:
                # Gửi trực tiếp tới Receptionist của Brain để test trí tuệ
                payload = {
                    "goal": q,
                    "task_id": f"stress_test_{i+1}",
                    "mode": "fast", # Test tốc độ phản xạ
                    "history": []
                }
                response = await client.post(BRAIN_URL, json=payload)
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "")
                    has_steps = "steps" in data
                    print(f"✅ [SUCCESS] Time: {duration:.2f}s | Type: {'Agentic' if has_steps else 'Chat'}")
                    results.append({
                        "id": i+1,
                        "question": q,
                        "status": "success",
                        "duration": duration,
                        "type": "agentic" if has_steps else "chat",
                        "answer_preview": str(answer)[:100] + "..."
                    })
                else:
                    print(f"❌ [FAILED] Status: {response.status_code}")
                    results.append({
                        "id": i+1,
                        "question": q,
                        "status": f"failed_{response.status_code}",
                        "duration": duration
                    })
            except Exception as e:
                duration = time.time() - start_time
                print(f"💥 [ERROR] {str(e)}")
                results.append({
                    "id": i+1,
                    "question": q,
                    "status": "error",
                    "error": str(e),
                    "duration": duration
                })
            
            # Nghỉ ngắn giữa các câu hỏi để tránh nghẽn VRAM quá mức
            await asyncio.sleep(0.5)

    # Tổng kết
    total_time = sum(r['duration'] for r in results)
    success_count = sum(1 for r in results if r['status'] == "success")
    avg_time = total_time / len(results)
    
    report = {
        "summary": {
            "total_questions": len(STRESS_QUESTIONS),
            "success": success_count,
            "failed": len(STRESS_QUESTIONS) - success_count,
            "avg_latency": avg_time,
            "total_duration": total_time
        },
        "details": results
    }
    
    with open("/storage/stress_test_50_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n🏁 [TEST COMPLETE]")
    print(f"📊 Thành công: {success_count}/{len(STRESS_QUESTIONS)}")
    print(f"⏱️ Latency trung bình: {avg_time:.2f}s")
    print(f"📜 Báo cáo chi tiết đã lưu tại /storage/stress_test_50_report.json")

if __name__ == "__main__":
    asyncio.run(run_test())
