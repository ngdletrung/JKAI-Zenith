"""
Tham dinh bang chung thuc thi (T5 Judicial Review) — fail-closed.

Truoc day /review_execution tra PASS voi accuracy_score 0.95 cho bat ky payload
nao khong chua status "error", tuc la tu bia bang chung. Mot ket qua chi duoc
tinh la bang chung khi executor bao ro trang thai thanh cong VA thuc su tra ve
du lieu.
"""

PROVEN_STATUSES = {"success", "completed"}


def _output_of(item: dict):
    for key in ("output", "answer", "msg", "result"):
        value = item.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def judge_execution_evidence(results) -> dict:
    if isinstance(results, list):
        items = results
    elif results:
        items = [results]
    else:
        items = []
    concrete = [item for item in items if isinstance(item, dict)]

    if not concrete:
        return {
            "verdict": "FAIL",
            "passed": False,
            "accuracy_score": 0.0,
            "feedback": "Executor produced no valid evidence.",
        }

    failed = [item for item in concrete if str(item.get("status", "")).lower() == "error"]
    if failed:
        return {
            "verdict": "FAIL",
            "passed": False,
            "accuracy_score": 0.0,
            "feedback": f"{len(failed)}/{len(concrete)} steps recorded errors.",
        }

    awaiting_auth = [
        item for item in concrete if str(item.get("status", "")).lower() == "needs_auth"
    ]
    if awaiting_auth:
        return {
            "verdict": "FAIL",
            "passed": False,
            "accuracy_score": 0.0,
            "feedback": "Execution paused for authorisation; evidence incomplete.",
        }

    proven = sum(
        1
        for item in concrete
        if str(item.get("status", "")).lower() in PROVEN_STATUSES and _output_of(item) is not None
    )
    score = round(proven / len(concrete), 2)

    if proven == len(concrete):
        return {
            "verdict": "PASS",
            "passed": True,
            "accuracy_score": score,
            "feedback": f"All {proven} steps returned concrete output.",
        }

    return {
        "verdict": "FAIL",
        "passed": False,
        "accuracy_score": score,
        "feedback": f"Only {proven}/{len(concrete)} steps returned concrete output.",
    }
