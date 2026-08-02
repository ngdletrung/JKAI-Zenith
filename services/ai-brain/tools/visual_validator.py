import re
import os
from typing import Dict, Any, List

class VisualValidator:
    """
    Bộ kiểm định chất lượng giao diện và cấu trúc DOM ngoại vi cho JKAI OS.
    Tự động rà soát mã HTML5, CSS và JavaScript theo các tiêu chuẩn thiết kế hiện đại
    (SEO, semantic HTML, responsive viewport, thẩm mỹ cao, không lặp ID).
    """

    def __init__(self):
        self.modern_fonts = ["inter", "roboto", "outfit", "poppins", "montserrat", "sans-serif"]

    def validate_ui_source(self, html_content: str, css_content: str = "") -> Dict[str, Any]:
        """
        Thực hiện đánh giá toàn bích cấu trúc giao diện ứng dụng.
        Trả về kết quả chấm điểm và danh sách lỗi thẩm mỹ hoặc cú pháp DOM cần sửa chữa.
        """
        issues: List[str] = []
        score = 100.0

        if not html_content.strip():
            return {"status": "error", "score": 0.0, "issues": ["Nội dung file giao diện trống."]}

        # 1. Kiểm tra chuẩn HTML5 Doctype & Viewport Responsive
        if "<!doctype html>" not in html_content.lower():
            issues.append("[HTML5] Thiếu khai báo <!DOCTYPE html> ở đầu tập tin.")
            score -= 15.0
        
        if not re.search(r'name=["\']viewport["\']', html_content, re.IGNORECASE):
            issues.append("[Responsive] Thiếu thẻ meta viewport để hiển thị linh hoạt trên thiết bị di động.")
            score -= 20.0

        # 2. Kiểm tra Thao tác SEO & Cấu trúc Thẻ Ngữ Nghĩa (Semantic HTML)
        h1_count = len(re.findall(r"<h1[^>]*>", html_content, re.IGNORECASE))
        if h1_count == 0:
            issues.append("[SEO] Không tìm thấy thẻ <H1> chủ đạo nào cho tiêu đề trang.")
            score -= 15.0
        elif h1_count > 1:
            issues.append("[SEO] Phát hiện nhiều hơn 1 thẻ <H1> trên trang (Vi phạm phân cấp ngữ nghĩa).")
            score -= 10.0

        for semantic_tag in ["header", "main", "footer"]:
            if f"<{semantic_tag}" not in html_content.lower():
                issues.append(f"[Semantic HTML] Should incorporate <{semantic_tag}> tag for accessible modern structure.")
                score -= 5.0

        # 3. Kiểm tra tính Độc Nhất của ID trên các phần tử tương tác
        ids = re.findall(r'id=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        seen_ids = set()
        for i in ids:
            if i in seen_ids:
                issues.append(f"[DOM Integrity] Phát hiện ID trùng lặp '{i}'. ID buộc phải là duy nhất.")
                score -= 10.0
            seen_ids.add(i)

        # 4. Thẩm định thiết kế CSS hiện đại (Modern Typography & Styling)
        combined_style = (html_content + " " + css_content).lower()
        has_modern_font = any(f in combined_style for f in self.modern_fonts)
        if not has_modern_font and "font-family" in combined_style:
            issues.append("[Aesthetics] Sử dụng font chữ mặc định cũ kỹ. Khuyên dùng Inter, Roboto hoặc Outfit.")
            score -= 10.0

        score = max(0.0, round(score, 2))
        status = "passed" if score >= 80.0 and not any("DOM Integrity" in idx for idx in issues) else "failed"

        return {
            "status": status,
            "score": score,
            "issue_count": len(issues),
            "issues": issues,
            "engine": "JKAI_VISUAL_VALIDATOR"
        }

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    validator = VisualValidator()

    # Mẫu HTML sai tiêu chuẩn hiện đại (Thiếu DOCTYPE, trụng ID, 2 thẻ H1, thiếu viewport)
    bad_html = """
    <html> # Thiếu DOCTYPE & viewport
      <head><title>Test App</title></head>
      <body>
        <h1 id="title">Main Title 1</h1>
        <h1 id="title">Duplicate Title 2</h1> # Trùng ID và thừa H1
        <button id="btn">Click me</button>
        <button id="btn">Submit</button> # Trùng ID btn
      </body>
    </html>
    """

    # Mẫu HTML đạt chuẩn thẩm mỹ & ngữ nghĩa Antigravity AI
    good_html = """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JKAI Sovereign Console</title>
        <style>body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; }</style>
      </head>
      <body>
        <header><h1>JKAI Personal OS</h1></header>
        <main><button id="btn-execute">Run Sovereign Protocol</button></main>
        <footer><p>Powered by Xeon & AMD RX 6600</p></footer>
      </body>
    </html>
    """

    res_bad = validator.validate_ui_source(bad_html)
    res_good = validator.validate_ui_source(good_html)

    print("=== VISUAL UI VALIDATOR BENCHMARK ===")
    print(f"Bad UI Test Score  : {res_bad['score']}/100 (Status: {res_bad['status']})")
    for iss in res_bad['issues'][:3]:
        print(f"  -> Detected Issue: {iss}")
        
    print(f"\nGood UI Test Score : {res_good['score']}/100 (Status: {res_good['status']})")
    
    if res_bad["status"] == "failed" and res_good["status"] == "passed" and res_good["score"] >= 95.0:
        print("\n[PASS] Bo Kiem Dinh Giao Dien Ngoai Vi hoat dong chinh xac tuyệt đối!")
    else:
        print("\n[FAIL] Kiem dinh chua dung quy chuân thê hien.")
