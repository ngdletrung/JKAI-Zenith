"""Mission 1 v2 (Calibration) — Module nghiep vu phi van chuyen.

QUY TAC PHONG THI: Agent chi duoc doc file nay qua view_file tai gio G.
Khong sua file nay bang tay — moi sua doi phai qua replace_file_content
cua Agent va duoc kiem chung bang pytest.
"""

FREE_SHIP_THRESHOLD = 500000
BASE_FEE = 30000
EXPRESS_MULT = 2


def shipping_fee(subtotal, express=False):
    """Phi ship: mien phi khi dat nguong, express nhan doi phi co ban."""
    if subtotal > FREE_SHIP_THRESHOLD:
        return 0
    fee = BASE_FEE
    if express:
        fee = fee * EXPRESS_MULT
    return fee
