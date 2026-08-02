import sys
import os
import asyncio

# The container already has /app and /shared in path, but let's add it explicitly
sys.path.append(r"/app")
sys.path.append(r"/shared")

from core.utils.engine import engine

async def main():
    print("Initializing test in container...")
    goal = "hãy cho tôi 5 tín tức mới nhất hôm nay về Trung Quốc"
    execution_results = [
        {
            "status": "success",
            "output": {
                "results": [
                    {"title": "Trung Quốc - Tin tức online 24h mới nhất hôm nay", "url": "https://example.com/1", "content": "Tin tức nóng hổi về tình hình kinh tế, chính trị Trung Quốc ngày hôm nay. Bắc Kinh vừa công bố gói kích thích kinh tế trị giá 100 tỷ USD nhằm hỗ trợ các doanh nghiệp công nghệ trong nước phát triển."},
                    {"title": "Tin tức, tình hình Trung Quốc mới nhất hôm nay", "url": "https://example.com/2", "content": "Trung Quốc đang đối mặt với những thách thức lớn về dân số khi tỷ lệ sinh tiếp tục giảm mạnh. Các chuyên gia xã hội đề xuất các chính sách hỗ trợ tài chính trực tiếp cho các gia đình trẻ."},
                    {"title": "Trung Quốc-Nga - Tin tức online 24h mới nhất hôm nay", "url": "https://example.com/3", "content": "Tổng thống Nga và Chủ tịch nước Trung Quốc vừa có cuộc hội đàm trực tuyến nhằm củng cố mối quan hệ hợp tác chiến lược toàn diện, tập trung vào lĩnh vực năng lượng và xuất nhập khẩu hàng hóa."}
                ]
            }
        }
    ]

    manifesto = await engine.get_brain_knowledge("agent_summarizer.md") or "Bạn là Thư ký Zenith T6."
    
    import datetime
    utc_now = datetime.datetime.utcnow()
    vietnam_now = utc_now + datetime.timedelta(hours=7)
    hour_min = vietnam_now.strftime("%Hh%M'")
    ampm = "AM" if vietnam_now.hour < 12 else "PM"
    hour_12 = vietnam_now.hour % 12
    if hour_12 == 0:
        hour_12 = 12
    formatted_time = f"{hour_12:02d}h{vietnam_now.minute:02d}' {ampm} ngày {vietnam_now.strftime('%d')} tháng {vietnam_now.strftime('%m')} năm {vietnam_now.strftime('%Y')}"

    # Replicate _compress_results logic directly
    compressed = json_compress(execution_results)

    summary_prompt = (
        f"[MISSION DATA]\n"
        f"Objective: {goal}\n"
        f"Execution Results: {compressed}\n\n"
        "══════════════════════════════════════════\n"
        "[SUMMARIZER PROTOCOL - TIN TỨC & URL]\n"
        "══════════════════════════════════════════\n"
        "You are the Elite Secretary of JKAI Zenith. Write a clear, comprehensive, and detailed news summary in Vietnamese.\n\n"
        "[CORE DIRECTIVES FOR WEBPAGE SUMMARY]\n"
        f"1. Dùng Tiêu đề của bài báo làm tiêu đề chính của báo cáo: '# Trung Quốc - Tin tức online 24h mới nhất hôm nay'.\n"
        "2. Tuyệt đối KHÔNG sử dụng các tiêu đề rập khuôn máy móc như '[BÁO CÁO ELITE]' hay '[MISSION_RESULT]'.\n"
        "3. Tuyệt đối KHÔNG viết câu vô nghĩa 'Mục tiêu Master đã được thực hiện' hay 'Kế hoạch đã được thực hiện'. Vào thẳng nội dung bài báo một cách tự nhiên, trang trọng và lịch thiệp.\n"
        "4. Trình bày bài tóm tắt ĐẦY ĐỦ, CHI TIẾT và CHUYÊN NGHIỆP. Không viết quá ngắn hay chung chung. Phân tích rõ các ý chính của bài viết, số liệu thống kê thực tế, những vấn đề tồn đọng hoặc các ý kiến của chuyên gia được nêu trong bài.\n"
        "5. CẤU TRÚC BẢN TIN CHUYÊN NGHIỆP: Sử dụng triệt để các dấu gạch đầu dòng (-) mạch lạc, rõ ràng để liệt kê các sự kiện/điểm tin chính. Tuyệt đối không viết thành các đoạn văn dài dòng, khó theo dõi. Mỗi gạch đầu dòng phải cô đọng, đi thẳng vào số liệu hoặc thông tin quan trọng.\n"
    )

    print("Calling engine.call_chat...")
    try:
        final_answer = await engine.call_chat(
            messages=[
                {"role": "system", "content": manifesto},
                {"role": "user", "content": summary_prompt},
            ],
            role="SUMMARIZER",
            task_id="test_summarizer_task",
            trace_id="test_trace"
        )
        
        signature = f"\n\n---\n👉 Tổng hợp lúc {formatted_time}\nBan Thư Ký JKAI Zenith"
        
        if isinstance(final_answer, dict) and "answer" in final_answer:
            final_answer["answer"] += signature
        elif isinstance(final_answer, str):
            final_answer += signature
            
        print("\n=== FINAL ANSWER ===")
        print(final_answer)
    except Exception as e:
        print(f"\n=== ERROR RAISED ===")
        print(e)

def json_compress(results):
    import json
    try:
        if isinstance(results, list):
            cleaned_list = []
            for res in results:
                if not isinstance(res, dict):
                    cleaned_list.append(res)
                    continue
                output_data = res.get("output", {})
                if isinstance(output_data, dict):
                    cleaned_output = {}
                    if "results" in output_data:
                        cleaned_results = []
                        for r in output_data.get("results", []):
                            if isinstance(r, dict):
                                cleaned_r = {
                                    "title": r.get("title", ""),
                                    "url": r.get("url", ""),
                                    "content": (r.get("content") or r.get("snippet") or "")[:1000]
                                }
                                cleaned_results.append(cleaned_r)
                        cleaned_output["results"] = cleaned_results
                    cleaned_res = {k: v for k, v in res.items() if k != "output"}
                    cleaned_res["output"] = cleaned_output
                    cleaned_list.append(cleaned_res)
                else:
                    cleaned_list.append(res)
            return json.dumps(cleaned_list, ensure_ascii=False)
    except Exception as e:
        print(f"Compress error: {e}")
    import json
    return json.dumps(results, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
