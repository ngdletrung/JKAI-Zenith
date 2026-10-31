---
aliases_vn:
- cau hinh mikrotik v6
- mikrotik routeros v6
- routeros 6 setup
- quan tri mikrotik v6
author: JKAI Sovereign Knowledge Forge
domain: DEVOPS
id: SKILL_MIKROTIK_V6_EXPERT
intent_pairs:
- - CONFIGURE
  - SKILL_MIKROTIK_V6_EXPERT
- - EXECUTE
  - SKILL_MIKROTIK_V6_EXPERT
name_vn: Kỹ năng Chuyên gia Cấu hình MikroTik RouterOS v6
priority: HIGH
related_skills:
- skill_quantrihethong
version: 1.0.0
---

# 🌐 KỸ NĂNG CHUYÊN GIA CẤU HÌNH MIKROTIK ROUTEROS V6 (SOVEREIGN NETWORK SUITE)

## 📖 1. TỔNG QUAN KIẾN TRÚC ROUTEROS V6

MikroTik RouterOS v6 vận hành trên nền tảng Linux Kernel 3.3.5 với cơ chế xử lý gói tin (Packet Flow v6) và cấu trúc quản trị đa kênh:
- **Kênh WebFig (HTTP/HTTPS - Port 80/443)**: Giao diện web trực quan đầy đủ, hiển thị cây menu quản trị thời gian thực cho `ai-browser` tương tác thị giác.
- **Kênh WinBox (Port 8291)**: Giao diện nhị phân độc quyền MikroTik chạy trên Windows hoặc qua Wine.
- **Kênh Terminal / CLI (SSH - Port 22, Telnet - Port 23)**: Dòng lệnh thực thi cấu hình theo cấu trúc thư mục dạng cây `/interface`, `/ip`, `/routing`, `/firewall`.

### Điểm khác biệt sống còn giữa RouterOS v6 và RouterOS v7:
1. **Routing Engine**: v6 sử dụng kiến trúc định tuyến đơn luồng truyền thống (`/routing ospf`, `/ip route` đơn giản). v7 tái cấu trúc hoàn toàn sang bảng routing mới.
2. **NAT Syntax**: Trên v6, lệnh NAT phổ biến là `/ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade` hoặc dùng interface list `WAN`.
3. **WireGuard**: v6 KHÔNG hỗ trợ WireGuard nguyên bản (muốn dùng VPN trên v6 phải dùng L2TP/IPSec, SSTP, OpenVPN TCP, PPTP).
4. **Bridge Hardware Offload**: v6 hỗ trợ HW-offload trên bridge cho các chip switch CRS/CRS3xx với cấu trúc VLAN filtering cụ thể.

---

## 🛠️ 2. MÔ HÌNH CẤU HÌNH CƠ BẢN 6 BƯỚC CHUẨN DOANH NGHIỆP (v6 SSoT)

```
[ISP / Internet]
       │ (WAN: ether1 - DHCP Client / PPPoE / Static IP)
[MikroTik RouterOS v6]
       │ (LAN Bridge: ether2 + ether3 + ether4 + ether5)
       ├── DHCP Server: 192.168.88.10 - 192.168.88.254
       ├── Gateway/DNS: 192.168.88.1 (DNS Caching Enabled)
       └── NAT Masquerade & Stateful Firewall
```

### Bước 1: Tạo Interface Bridge và Gom Cổng LAN
```routeros
/interface bridge add name=bridge-LAN comment="LAN Core Bridge"
/interface bridge port add bridge=bridge-LAN interface=ether2
/interface bridge port add bridge=bridge-LAN interface=ether3
/interface bridge port add bridge=bridge-LAN interface=ether4
/interface bridge port add bridge=bridge-LAN interface=ether5
```

### Bước 2: Thiết lập Cổng WAN (Đa kịch bản)
* **Kịch bản A — WAN nhận IP động từ Modem/ISP (DHCP Client)**:
  ```routeros
  /ip dhcp-client add interface=ether1 disabled=no use-peer-dns=yes use-peer-ntp=yes add-default-route=yes
  ```
* **Kịch bản B — WAN quay số PPPoE trực tiếp (Cáp quang FTTH)**:
  ```routeros
  /interface pppoe-client add name=pppoe-out1 interface=ether1 user="FTTH_ACCOUNT" password="FTTH_PASSWORD" add-default-route=yes disabled=no
  ```
* **Kịch bản C — WAN gán IP tĩnh (Static IP)**:
  ```routeros
  /ip address add address=203.0.113.10/24 interface=ether1 network=203.0.113.0
  /ip route add gateway=203.0.113.1 distance=1
  ```

### Bước 3: Đặt Địa Chỉ IP Cho Mạng Nội Bộ (LAN Gateway)
```routeros
/ip address add address=192.168.88.1/24 interface=bridge-LAN network=192.168.88.0
```

### Bước 4: Thiết lập Dịch Vụ Cấp Phát IP Tự Động (DHCP Server)
```routeros
/ip pool add name=pool-LAN ranges=192.168.88.10-192.168.88.254
/ip dhcp-server add name=dhcp-LAN interface=bridge-LAN address-pool=pool-LAN disabled=no lease-time=12h
/ip dhcp-server network add address=192.168.88.0/24 gateway=192.168.88.1 dns-server=192.168.88.1,8.8.8.8 comment="LAN Subnet DHCP Option"
```

### Bước 5: Cấu Hình DNS Caching & Phân Giải Tên Miền
```routeros
/ip dns set allow-remote-requests=yes servers=8.8.8.8,1.1.1.1
```

### Bước 6: Tường Lửa (Firewall Filter) & NAT Masquerade
* **NAT Masquerade để ra Internet**:
  ```routeros
  /ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade comment="NAT Masquerade WAN"
  # (Nếu dùng PPPoE thì out-interface=pppoe-out1)
  ```
* **Quy tắc Tường lửa Stateful Protection (Chống xâm nhập từ WAN)**:
  ```routeros
  # Input Chain (Bảo vệ chính thiết bị Router)
  /ip firewall filter add chain=input connection-state=established,related action=accept comment="Accept Established/Related"
  /ip firewall filter add chain=input connection-state=invalid action=drop comment="Drop Invalid Connections"
  /ip firewall filter add chain=input in-interface=bridge-LAN action=accept comment="Allow LAN to Router Management"
  /ip firewall filter add chain=input protocol=icmp action=accept comment="Allow ICMP Ping for Diagnostics"
  /ip firewall filter add chain=input action=drop comment="Drop all other WAN input (Anti-Scan/Bruteforce)"

  # Forward Chain (Bảo vệ các thiết bị trong mạng LAN)
  /ip firewall filter add chain=forward connection-state=established,related action=accept comment="Accept Established/Related Forward"
  /ip firewall filter add chain=forward connection-state=invalid action=drop comment="Drop Invalid Forward"
  /ip firewall filter add chain=forward in-interface=bridge-LAN out-interface=ether1 action=accept comment="Allow LAN to Internet"
  /ip firewall filter add chain=forward action=drop comment="Drop all other forward"
  ```

---

## 🖥️ 3. QUY TRÌNH THỰC THI TRỰC QUAN TRÊN GIAO DIỆN WEBFIG (CHO AI-BROWSER)

Khi `ai-browser` điều khiển trực quan qua WebFig (`http://192.168.88.1`):

1. **Khung nhìn Đăng nhập**:
   - Selector: `input[name="username"]` -> điền `admin`.
   - Selector: `input[name="password"]` -> điền mật khẩu -> Nhấn `Login`.
2. **Khung nhìn Menu Trực quan (Left Sidebar Navigation)**:
   - `Bridge`: Tạo bridge và thêm cổng thành viên.
   - `IP -> Addresses`: Gán địa chỉ IP cho các interface.
   - `IP -> DHCP Server`: Thiết lập DHCP Setup wizard tự động.
   - `IP -> DNS`: Tích chọn `Allow Remote Requests`.
   - `IP -> Firewall`: Chuyển sang tab `NAT` -> Thêm rule `srcnat` + `action=masquerade`.
3. **Chụp hình ảnh trực quan (Visual Telemetry)**:
   - Sau mỗi bước cấu hình, chụp ảnh màn hình WebFig gửi về Mission Control (`http://localhost:9999/`) với tiêu đề chú thích từng bước.

---

## ⚠️ 4. CÁC SAI LẦM KINH ĐIỂN VÀ CÁCH PHÒNG TRÁNH (PITFALLS)

1. **Lockout Router khi tạo Bridge**:
   - *Lỗi*: Gán cổng đang cắm cáp quản trị vào bridge mà chưa chuyển IP của router sang interface bridge.
   - *Phòng tránh*: Bật chế độ **Safe Mode** (`Ctrl + X` trong CLI hoặc nút *Safe Mode* màu xanh ở góc trên WebFig). Nếu cấu hình làm mất kết nối, router tự động rollback về trạng thái trước đó sau 10 giây.
2. **DNS Amplification Attack**:
   - *Lỗi*: Bật `allow-remote-requests=yes` nhưng không tạo rule chặn cổng UDP/TCP 53 từ cổng WAN. Router sẽ bị tin tặc lợi dụng làm bàn đạp tấn công DDOS DNS toàn cầu.
   - *Khắc phục*: Quy tắc firewall input `drop all other WAN input` đã bao trùm chặn cổng 53 từ bên ngoài.
3. **Trùng Subnet WAN và LAN**:
   - *Lỗi*: Modem nhà mạng cấp dải `192.168.1.0/24`, nhưng mạng LAN MikroTik cũng đặt `192.168.1.0/24` dẫn đến xung đột routing.
   - *Quy chuẩn*: Đặt dải LAN MikroTik là `192.168.88.0/24` hoặc `10.10.10.0/24`.
