"""Mission 1 (Calibration) — Module nghiep vu tinh tien hoa don.

QUY TAC PHONG THI: Agent chi duoc doc file nay qua view_file tai gio G.
Khong sua file nay bang tay — moi sua doi phai qua replace_file_content
cua Agent va duoc kiem chung bang pytest.
"""

VAT_RATE = 0.10


def calc_subtotal(items):
    """items: list (price, qty). Tra ve tong tien truoc giam gia."""
    return sum(price * qty for price, qty in items)


def calc_total(items, discount_pct):
    """Tong thanh toan = (subtotal - giam gia) + VAT 10%."""
    subtotal = calc_subtotal(items)
    discount = subtotal * discount_pct / 100
    after_discount = subtotal - discount
    vat = after_discount * VAT_RATE
    return after_discount + vat - discount
