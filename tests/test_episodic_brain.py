#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/test_episodic_brain.py
Kiểm thử bộ não ngoài (Episodic Multi-Domain Memory Brain):
1. Ingest & Recall Semantic Match
2. Domain Isolation (Cách ly lĩnh vực)
3. Strict Similarity Gate (Cổng chặn < 0.75)
"""

import sys
import os
import pytest

from core.memory.episodic_brain import episodic_brain, DOMAINS, THETA_UNFIT_PLACEHOLDER

def test_01_ensure_collection_and_domain_index():
    """Đảm bảo collection và index domain được tạo thành công trên Qdrant."""
    ready = episodic_brain._ensure_collection()
    assert ready is True, "Qdrant collection initialization failed"
    print("✅ TEST 1 PASS: Qdrant collection ready with domain indexing")

def test_02_ingest_and_recall_math_positive():
    """Nạp mẫu chuẩn toán học và kiểm tra truy xuất tương đồng."""
    goal_seed = "240 thùng hàng, xe tải chở được 30 thùng/chuyến. Phí xăng mỗi chuyến 400k, tổng phí xăng là bao nhiêu?"
    resp_seed = "Để vận chuyển hết 240 thùng hàng với công suất 30 thùng/chuyến: Cần 8 chuyến. Tổng chi phí xăng là 3.200.000 đồng."
    
    ok = episodic_brain.ingest_exemplar(
        record_id="GOLD_TEST_MATH_01",
        goal=goal_seed,
        response=resp_seed,
        verdict="ACCEPT",
        domain="MATH",
        lesson="Bảo toàn đơn vị thùng và phí xăng"
    )
    assert ok is True, "Failed to ingest gold exemplar"

    # Query tương đồng: câu hỏi viết lại nhưng cùng ngữ nghĩa toán
    query = "Một lô 240 thùng hàng cần chuyển, xe tải chở 30 thùng một chuyến, tiền xăng 400 nghìn một chuyến thì hết bao nhiêu tiền?"
    results = episodic_brain.recall_relevant_exemplars(query, domain="MATH", threshold=0.70)
    
    assert len(results) > 0, "Failed to recall semantic match"
    hit = results[0]
    assert hit.record_id == "GOLD_TEST_MATH_01"
    assert hit.domain == "MATH"
    assert hit.verdict == "ACCEPT"
    assert hit.similarity_score >= 0.70
    print(f"✅ TEST 2 PASS: Semantic Match thành công (Similarity: {hit.similarity_score:.4f})")

def test_03_domain_isolation():
    """Kiểm tra cách ly lĩnh vực: truy vấn domain CODE_FILEOPS không được lọt ca MATH."""
    query = "Một lô 240 thùng hàng cần chuyển, xe tải chở 30 thùng một chuyến"
    # Lọc domain CODE_FILEOPS
    results = episodic_brain.recall_relevant_exemplars(query, domain="CODE_FILEOPS", threshold=0.50)
    assert len(results) == 0, f"FAIL: Domain isolation bị thủng! Lọt {len(results)} kết quả"
    print("✅ TEST 3 PASS: Domain Isolation tuyệt đối (Không rò rỉ kiến thức giữa các lĩnh vực)")

def test_04_strict_threshold_rejection():
    """Kiểm tra cổng chặn: câu hỏi không liên quan (< 0.75) tuyệt đối không được trả về."""
    irrelevant_query = "Thời tiết Hà Nội hôm nay thế nào có mưa không?"
    results = episodic_brain.recall_relevant_exemplars(irrelevant_query, domain="MATH", threshold=THETA_UNFIT_PLACEHOLDER)
    assert len(results) == 0, "FAIL: Cổng chặn lỏng lẻo, trả về kết quả không liên quan"
    print("✅ TEST 4 PASS: Strict Gate chặn đứng câu hỏi ngoài vùng tương đồng")

def test_05_format_prompt_provenance():
    """Kiểm tra định dạng prompt và truy vết nguồn gốc record_id."""
    from core.memory.episodic_brain import MemoryExemplar
    ex = MemoryExemplar(
        record_id="GOLD_TEST_REF_99",
        domain="MATH",
        goal="240 thùng",
        exemplar_response="8 chuyến, 3.2M",
        verdict="ACCEPT",
        lesson="Bảo toàn đơn vị",
        similarity_score=0.88
    )
    prompt = episodic_brain.format_context_prompt([ex])
    assert "GOLD_TEST_REF_99" in prompt
    assert "EPISODIC-POSITIVE-EXEMPLAR" in prompt
    assert "0.88" in prompt
    print("✅ TEST 5 PASS: Provenance & Prompt formatting hoàn hảo")

def test_06_task_taxonomy_mikrotik_and_java():
    """Kiểm tra taxonomy việc: NET_MIKROTIK và CODE_JAVA cách ly hoàn toàn."""
    # 1. Nạp mẫu chuẩn MikroTik
    episodic_brain.ingest_exemplar(
        record_id="GOLD_NET_MIKROTIK_01",
        goal="Cấu hình DHCP Server trên cổng ether2 RouterOS MikroTik",
        response="/ip dhcp-server add interface=ether2 name=dhcp-lan address-pool=pool-lan disabled=no",
        verdict="ACCEPT",
        task_code="NET_MIKROTIK",
        lesson="Tuân thủ cú pháp RouterOS CLI"
    )

    # 2. Nạp mẫu chuẩn Java
    episodic_brain.ingest_exemplar(
        record_id="GOLD_CODE_JAVA_01",
        goal="Viết Spring Boot RestController trả về danh sách sinh viên",
        response="@RestController @RequestMapping('/api/students') public class StudentController { ... }",
        verdict="ACCEPT",
        task_code="CODE_JAVA",
        lesson="Sử dụng chuẩn Spring Boot 3"
    )

    # 3. Truy vấn câu hỏi Java vào kho MikroTik -> bắt buộc rỗng (Quy tắc sắt 1)
    res_leak = episodic_brain.recall_relevant_exemplars(
        "Viết code Spring Boot Java",
        task_code="NET_MIKROTIK",
        threshold=0.50
    )
    assert len(res_leak) == 0, "FAIL: Quy tắc sắt 1 bị vi phạm: Java lọt vào kho MikroTik!"

    # 4. Truy vấn câu hỏi MikroTik vào đúng kho -> phải trúng
    res_hit = episodic_brain.recall_relevant_exemplars(
        "Cách tạo DHCP server trên RouterOS MikroTik ether2",
        task_code="NET_MIKROTIK",
        threshold=0.70
    )
    assert len(res_hit) > 0, "FAIL: Không tìm thấy bài học MikroTik trong kho!"
    assert res_hit[0].record_id == "GOLD_NET_MIKROTIK_01"
    print("✅ TEST 6 PASS: Taxonomy 2 tầng NET_MIKROTIK & CODE_JAVA cách ly tuyệt đối")

def test_07_iron_rule_2_out_of_scope_rejection():
    """Quy tắc sắt 2: Mã việc không có / ngoài phạm vi thì cấm đoán mò -> trả về rỗng."""
    from core.memory.episodic_brain import classify_task
    # Câu hỏi không liên quan đến bất kỳ việc nào đã định nghĩa
    irrelevant = "con chim bay trên trời xanh lơ lửng"
    code = classify_task(irrelevant)
    assert code is None, "FAIL: Phân loại phải trả về None cho yêu cầu ngoài phạm vi!"

    # Khi mã việc rỗng, recall_relevant_exemplars phải từ chối ngay lập tức
    results = episodic_brain.recall_relevant_exemplars(irrelevant, task_code=code)
    assert len(results) == 0, "FAIL: Cấm đoán bừa bãi khi ngoài phạm vi!"
    print("✅ TEST 7 PASS: Quy tắc sắt 2 chặn đứng việc bốc bừa ngoài phạm vi")

def test_08_learn_from_feedback_immediate():
    """Cơ chế học hỏi & sửa sai ngay lập tức (Continuous Active Correction)."""
    goal = "Cấu hình NAT masquerade cho mạng ra internet trên MikroTik"
    wrong_ans = "iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE"  # Sai: nhầm Linux với RouterOS
    correct_ans = "/ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade"

    feedback_res = episodic_brain.learn_from_feedback(
        record_id="FEEDBACK_NAT_01",
        goal=goal,
        wrong_response=wrong_ans,
        correct_response=correct_ans,
        task_code="NET_MIKROTIK",
        lesson="MikroTik RouterOS cấm dùng lệnh iptables của Linux"
    )

    assert feedback_res["negative_stored"] is True, "FAIL: Chưa lưu vết xe đổ!"
    assert feedback_res["positive_stored"] is True, "FAIL: Chưa lưu chuẩn vàng!"

    # Ngay lập tức kiểm tra truy xuất: phải bốc được bài học vết xe đổ lẫn chuẩn vàng
    exemplars = episodic_brain.recall_relevant_exemplars(
        "Lệnh NAT masquerade ra net trên RouterOS MikroTik",
        task_code="NET_MIKROTIK",
        top_k=2,
        threshold=0.70
    )
    assert len(exemplars) >= 1, "FAIL: Bài học mới chưa sẵn sàng ngay lập tức!"
    print("✅ TEST 8 PASS: Học hỏi và cập nhật đúng ngay lập tức (Sub-50ms)")

def test_09_dynamic_new_task_registration():
    """Kiểm tra khi có mã việc mới phát sinh: Đăng ký động, lưu file, dùng ngay lập tức."""
    from core.memory.episodic_brain import register_new_task_code, classify_task

    # 1. Đăng ký mã việc mới chưa từng tồn tại: NET_FORTINET
    reg_res = register_new_task_code(
        task_code="NET_FORTINET",
        name="Tường lửa Fortinet / FortiGate (FortiOS, VDOM, Policy)",
        subs=["VDOM", "HA", "FIREWALL_POLICY", "IPSEC"],
        keywords=["fortinet", "fortigate", "fortios", "vdom", "firewall policy"],
        aliases=["FORTIGATE", "FORTIOS"]
    )
    assert reg_res["success"] is True, f"FAIL: Đăng ký mã việc mới thất bại: {reg_res}"

    # 2. Tự động nhận diện câu hỏi theo mã việc mới vừa tạo
    query = "Cách tạo Firewall Policy cho phép LAN ra WAN trên FortiGate"
    detected_code = classify_task(query)
    assert detected_code == "NET_FORTINET", f"FAIL: Không nhận diện được mã việc mới! Got: {detected_code}"

    # 3. Nạp mẫu chuẩn vào kho mới
    ok = episodic_brain.ingest_exemplar(
        record_id="GOLD_FORTI_01",
        goal=query,
        response="config firewall policy\nedit 1\nset srcintf 'lan'\nset dstintf 'wan1'\nset action accept\nnext\nend",
        verdict="ACCEPT",
        task_code="NET_FORTINET",
        lesson="Cú pháp CLI FortiOS chuẩn"
    )
    assert ok is True, "FAIL: Không thể nạp mẫu chuẩn vào kho việc mới tạo!"

    # 4. Truy xuất ngay lập tức từ kho việc mới
    hits = episodic_brain.recall_relevant_exemplars(
        "Tạo firewall policy trên Fortinet FortiGate",
        task_code="NET_FORTINET",
        threshold=0.70
    )
    assert len(hits) > 0, "FAIL: Không truy xuất được từ kho việc mới!"
    assert hits[0].record_id == "GOLD_FORTI_01"
    print("✅ TEST 9 PASS: Đăng ký mã việc mới động (Dynamic Task Registry) hoạt động hoàn hảo")

if __name__ == "__main__":
    test_01_ensure_collection_and_domain_index()
    test_02_ingest_and_recall_math_positive()
    test_03_domain_isolation()
    test_04_strict_threshold_rejection()
    test_05_format_prompt_provenance()
    test_06_task_taxonomy_mikrotik_and_java()
    test_07_iron_rule_2_out_of_scope_rejection()
    test_08_learn_from_feedback_immediate()
    test_09_dynamic_new_task_registration()
    print("\nALL 9/9 EPISODIC BRAIN TESTS PASSED! 🧠⚡✅")


