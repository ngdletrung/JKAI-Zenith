---
id: FIN_03_WHALE_TRACK
name_vn: "Truy Vết Cá Mập Crypto"
version: 1.0.0
author: "Antigravity Forge"
domain: FINANCE
intent_pairs:
  - ["TRACK", "WHALE"]
  - ["MONITOR", "CRYPTO"]
aliases_vn: ["theo dõi cá mập", "whale track", "truy vết ví", "crypto tracker"]
schema:
  parameters:
    type: object
    properties:
      wallet_address: { type: string, description: "Địa chỉ ví cần truy vết." }
      network: { type: string, description: "Mạng lưới (VD: ETH, BSC, SOL)." }
    required: ["wallet_address"]
priority: NORMAL
related_skills: ["FIN_02_TECH_ANALYSIS"]
---

# 🐋 TRUY VẾT CÁ MẬP CRYPTO (FIN_03_WHALE_TRACK)

## 🌟 TỔNG QUAN
Kỹ năng này chịu trách nhiệm giám sát các biến động số dư lớn từ các ví "Cá mập" trên các mạng lưới Blockchain.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Xác minh Địa chỉ**: Kiểm tra tính hợp lệ của `wallet_address` trên mạng lưới `network`.
2. **Trinh sát On-chain**: Truy vấn lịch sử giao dịch gần nhất từ các API Explorer (Etherscan, Solscan).

### 🚀 Phase 2: Action (Thực thi)
1. **Phân tích Biến động**: Nhận diện các lệnh nạp/rút lớn có khả năng tác động đến thị trường.
2. **Cảnh báo Master**: Trả về báo cáo chi tiết về hành vi của "Cá mập".

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Theo dõi các ví "sống" nhưng không có hoạt động gây lãng phí tài nguyên.
- Nhầm lẫn giữa ví sàn (Exchange Wallet) và ví cá nhân.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
