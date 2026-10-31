# -*- coding: utf-8 -*-
"""Core tests for AnswerQualityVerifier."""
from core.os.cognition.answer_quality_verifier import answer_quality_verifier


class TestAnswerQualityCore:
    def test_01_master_standard_answer_passes_all(self):
        text = "Chào Master, ngày hôm nay là Chủ nhật. Bạn cần tôi hỗ trợ gì thêm không?"
        r = answer_quality_verifier.verify(text, goal="hôm nay là thứ mấy")
        assert r.overall_passed is True
        assert r.overall_score == 1.0

    def test_02_internal_leak_fails_dung(self):
        text = "Chào Master, kết quả STAGE_4_1_DETERMINISTIC đã xong ở world_version mới."
        r = answer_quality_verifier.verify(text, goal="kiểm tra trạng thái")
        assert r.dung.passed is False
        assert r.overall_passed is False

    def test_03_direct_answer_passes_du(self):
        """Câu trả lời trực tiếp không cần greeting — AQV không được tự bổ sung."""
        text = ("Báo cáo phân tích của bạn đã hoàn thành đầy đủ với tất cả "
                "các chỉ số được tổng hợp chi tiết theo từng hạng mục yêu cầu.")
        r = answer_quality_verifier.verify(text, goal="báo cáo phân tích")
        assert r.corrected_text is None
        assert r.du.passed is True

    def test_04_verbose_off_goal_fails_trung(self):
        goal = "doanh thu quý 3 theo từng chi nhánh"
        text = ("Nói về thời tiết hôm nay thì trời trong xanh và có nắng nhẹ "
                "trên khắp các khu vực miền Trung với nhiệt độ ổn định " * 8)
        r = answer_quality_verifier.verify(text, goal=goal)
        assert r.trung.passed is False

    def test_05_unsourced_claim_fails_dung(self):
        text = "Chào Master, theo nghiên cứu thì phương pháp này hiệu quả vượt trội."
        r = answer_quality_verifier.verify(text, goal="đánh giá phương pháp")
        assert r.dung.passed is False
        assert r.needs_escalate is True

    def test_06_greeting_social_not_flagged_for_missing_keywords(self):
        goal = "Xin chào, bạn là ai và bạn có thể làm được những gì?"
        text = ("Chào mừng Master. Tôi là JKAI Zenith - Hệ điều hành Trí tuệ Nhân tạo thế hệ mới. "
                "Tôi được trang bị cụm mô hình hợp tác đa tác nhân, có khả năng phân tích lập trình, "
                "truy vấn dữ liệu, điều phối công cụ tự động và vận hành các kịch bản chuyên sâu. " * 5)
        r = answer_quality_verifier.verify(text, goal=goal)
        assert r.trung.passed is True
        assert r.overall_passed is True

    def test_07_table_math_inconsistent_fails_dung(self):
        bad_table = (
            "| STT | Nguyên liệu | Số lượng | Đơn giá | Thành tiền |\n"
            "| :---: | :--- | :---: | :---: | :---: |\n"
            "| 1 | Thịt bò | ~350g | 28.000đ/kg | 98.000đ |\n"
        )
        r_bad = answer_quality_verifier.verify(bad_table, goal="thực đơn")
        assert r_bad.dung.passed is False
        assert r_bad.overall_passed is False

        mismatch_total_table = (
            "| STT | Nguyên liệu | Số lượng | Đơn giá | Thành tiền |\n"
            "| :---: | :--- | :---: | :---: | :---: |\n"
            "| 1 | Thịt bò tươi | 300g | 270.000đ/kg | 81.000đ |\n"
            "| 2 | Thịt heo xay | 200g | 135.000đ/kg | 27.000đ |\n"
            "| - | TỔNG CHI PHÍ | - | - | 274.500đ |\n"
        )
        r_mismatch = answer_quality_verifier.verify(mismatch_total_table, goal="thực đơn")
        assert r_mismatch.dung.passed is False
        assert any("Lỗi tổng chi phí" in iss for iss in r_mismatch.dung.issues)

        good_table = (
            "| STT | Nguyên liệu | Số lượng | Đơn giá | Thành tiền |\n"
            "| :---: | :--- | :---: | :---: | :---: |\n"
            "| 1 | Thịt bò tươi | 300g | 270.000đ/kg | 81.000đ |\n"
            "| 2 | Thịt heo xay | 200g | 135.000đ/kg | 27.000đ |\n"
        )
        r_good = answer_quality_verifier.verify(good_table, goal="thực đơn")
        assert r_good.dung.passed is True
        assert r_good.overall_passed is True

    def test_08_time_consistency_fails_dung(self):
        bad_text = (
            "### Quy trình nấu nướng tối ưu chạm 32 phút\n"
            "Giai đoạn 1: Sơ chế đồng loạt - Tổng thời gian: 18 phút\n"
            "Giai đoạn 2: Nấu song song 2 bếp - Tổng thời gian: 15 phút\n"
            "Giai đoạn 3: Hoàn thiện lên mâm - Tổng thời gian: 7 phút\n"
        )
        r_bad = answer_quality_verifier.verify(bad_text, goal="nấu ăn")
        assert r_bad.dung.passed is False
        assert any("Mâu thuẫn thời gian" in issue for issue in r_bad.dung.issues)

        good_text = (
            "### Quy trình nấu nướng tối ưu trong 35 phút\n"
            "Giai đoạn 1: Sơ chế đồng loạt - Tổng thời gian: 15 phút\n"
            "Giai đoạn 2: Nấu song song 2 bếp - Tổng thời gian: 15 phút\n"
            "Giai đoạn 3: Hoàn thiện lên mâm - Tổng thời gian: 5 phút\n"
        )
        r_good = answer_quality_verifier.verify(good_text, goal="nấu ăn")
        assert r_good.dung.passed is True

    def test_09_nutrition_gate_fails_dung(self):
        goal = "Gợi ý thực đơn bữa tối 3 món đủ chất cho gia đình 4 người"
        bad_menu = (
            "Thực đơn gồm: Bò xào cần tỏi, Thịt băm viên sốt cà chua, Canh rau muống luộc dầm sấu. "
            "Rất thơm ngon và bổ dưỡng."
        )
        r_bad = answer_quality_verifier.verify(bad_menu, goal=goal)
        assert r_bad.dung.passed is False
        assert any("thiếu nhóm tinh bột" in issue for issue in r_bad.dung.issues)

        good_menu = (
            "Thực đơn gồm: Bò xào cần tỏi, Thịt băm viên sốt cà chua, Canh rau muống luộc dầm sấu, "
            "ăn kèm cơm trắng dẻo thơm từ gạo tẻ mới nấu."
        )
        r_good = answer_quality_verifier.verify(good_menu, goal=goal)
        assert r_good.dung.passed is True

    def test_10_step_duration_exceeds_phase_duration_fails_dung(self):
        bad_text = (
            "### Lộ trình nấu 35 phút\n"
            "Giai đoạn 1: Sơ chế và chuẩn bị | Thời gian: 15 phút\n"
            "- Ướp thịt: Hầm nhẹ 20 phút cho thịt bò ngấm gia vị.\n"
            "Giai đoạn 2: Nấu song song 2 bếp | Thời gian: 15 phút\n"
            "- Nấu canh trong 10 phút.\n"
            "Giai đoạn 3: Hoàn thiện | Thời gian: 5 phút\n"
        )
        r_bad = answer_quality_verifier.verify(bad_text, goal="nấu ăn")
        assert r_bad.dung.passed is False
        assert any("vượt quá thời lượng giai đoạn" in iss for iss in r_bad.dung.issues)

        good_text = (
            "### Lộ trình nấu 35 phút\n"
            "Giai đoạn 1: Sơ chế và chuẩn bị | Thời gian: 15 phút\n"
            "- Ướp thịt: Ướp nhanh 5 phút cho thịt bò ngấm gia vị.\n"
            "Giai đoạn 2: Nấu song song 2 bếp | Thời gian: 15 phút\n"
            "- Nấu canh trong 10 phút.\n"
            "Giai đoạn 3: Hoàn thiện | Thời gian: 5 phút\n"
        )
        r_good = answer_quality_verifier.verify(good_text, goal="nấu ăn")
        assert r_good.dung.passed is True

    def test_11_four_nutrition_groups_fails_dung_on_three_groups(self):
        goal = "thực đơn bữa tối đủ chất cho gia đình"
        bad_text = (
            "Thực đơn gồm cơm trắng, bò xào, canh cải. "
            "Kết quả: Bữa ăn cân bằng với 3 nhóm chất chính là đạm, tinh bột, vitamin."
        )
        r_bad = answer_quality_verifier.verify(bad_text, goal=goal)
        assert r_bad.dung.passed is False
        assert any("3 nhóm chất" in iss for iss in r_bad.dung.issues)

        good_text = (
            "Thực đơn gồm cơm trắng, bò xào, canh cải. "
            "Kết quả: Bữa ăn cân bằng với đầy đủ 4 nhóm chất: đạm, tinh bột, xơ/vitamin và chất béo."
        )
        r_good = answer_quality_verifier.verify(good_text, goal=goal)
        assert r_good.dung.passed is True

    def test_12_burner_count_consistency_fails_dung(self):
        bad_text = (
            "### Lộ trình nấu song song 2 bếp\n"
            "- Bếp 1: Nấu canh 15 phút.\n"
            "- Bếp 2: Xào bò 7 phút.\n"
            "- Bếp phụ: Xào rau muống 5 phút.\n"
        )
        r_bad = answer_quality_verifier.verify(bad_text, goal="nấu ăn")
        assert r_bad.dung.passed is False
        assert any("Mâu thuẫn thiết bị nấu" in iss for iss in r_bad.dung.issues)

        good_text = (
            "### Lộ trình nấu song song 2 bếp\n"
            "- Bếp 1: Nấu canh 15 phút.\n"
            "- Bếp 2: Xào bò 7 phút, sau đó xào tiếp rau muống 5 phút.\n"
        )
        r_good = answer_quality_verifier.verify(good_text, goal="nấu ăn")
        assert r_good.dung.passed is True

    def test_13_timeline_addition_consistency_fails_dung(self):
        bad_text = (
            "Giai đoạn 1: Sơ chế | Thời gian: 15 phút\n"
            "Giai đoạn 2: Nấu song song | Thời gian: 15 phút\n"
            "Bữa ăn hoàn chỉnh: 30 phút chuẩn bị + 5 phút nấu = 35 phút\n"
        )
        r_bad = answer_quality_verifier.verify(bad_text, goal="nấu ăn")
        assert r_bad.dung.passed is False
        assert any("Mô tả thời gian không nhất quán" in iss for iss in r_bad.dung.issues)

        good_text = (
            "Giai đoạn 1: Sơ chế | Thời gian: 15 phút\n"
            "Giai đoạn 2: Nấu song song | Thời gian: 15 phút\n"
            "Bữa ăn hoàn chỉnh: 15 phút chuẩn bị + 15 phút nấu + 5 phút lên mâm = 35 phút\n"
        )
        r_good = answer_quality_verifier.verify(good_text, goal="nấu ăn")
        assert r_good.dung.passed is True

    def test_14_combo_spice_oil_passes_dung(self):
        combo_table = (
            "| STT | Nguyên liệu | Số lượng | Đơn giá | Thành tiền |\n"
            "| :---: | :--- | :---: | :---: | :---: |\n"
            "| 1 | Thịt bò tươi | 300g | 270.000đ/kg | 81.000đ |\n"
            "| 2 | Dầu ăn & Gia vị | 50ml dầu + 30g gia vị | 15.000đ/phần | 15.000đ |\n"
            "| - | TỔNG CỘNG | - | - | 96.000đ |\n"
        )
        r = answer_quality_verifier.verify(combo_table, goal="thực đơn")
        assert r.dung.passed is True
        assert r.overall_passed is True

    def test_15_nutrition_wording_and_kcal_assertions(self):
        goal = "thực đơn bữa tối 3 món đủ chất cho gia đình"
        # Bị fail vì claim kcal không nguồn
        kcal_text = (
            "Thực đơn gồm cơm trắng, thịt bò xào, canh rau. "
            "Dầu ăn và gia vị cung cấp ~48kcal năng lượng."
        )
        r_kcal = answer_quality_verifier.verify(kcal_text, goal=goal)
        assert r_kcal.dung.passed is False
        assert any("thông tin năng lượng" in iss for iss in r_kcal.dung.issues)

        # Bị fail vì gán nhãn tinh bột cho thịt bò xào
        mismatch_carb = (
            "Món mặn chính (Protein & Tinh bột): Thịt bò xào hành tây. "
            "Canh rau muống và cơm trắng."
        )
        r_carb = answer_quality_verifier.verify(mismatch_carb, goal=goal)
        assert r_carb.dung.passed is False
        assert any("Mâu thuẫn phân loại dinh dưỡng" in iss for iss in r_carb.dung.issues)

        # Hợp lệ chuẩn xác
        good_text = (
            "Món mặn chính (Protein): Thịt bò xào hành tây. "
            "Món canh: Canh đậu phụ rau muống. "
            "Ăn kèm: Cơm trắng dẻo thơm (nguồn tinh bột duy nhất). "
            "Phân loại đầy đủ 4 nhóm chất: Đạm, Tinh bột, Xơ/Vitamin, Chất béo."
        )
        r_good = answer_quality_verifier.verify(good_text, goal=goal)
        assert r_good.dung.passed is True
