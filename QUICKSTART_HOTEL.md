# ⚡ Hotel Reservation System - Quick Start

3 ขั้นตอนเริ่มต้นใช้งาน

## 📦 ขั้นตอนที่ 1: ติดตั้ง (1 นาที)

```bash
pip install -r requirements_hotel.txt
```

**Packages ที่ติดตั้ง:**
- ✅ fastapi - Web framework
- ✅ uvicorn - ASGI server
- ✅ httpx - HTTP client
- ✅ mcp - Model Context Protocol
- ✅ pyjwt - JWT authentication

---

## 🚀 ขั้นตอนที่ 2: รัน FastAPI Server (ใช้ Terminal 1)

```bash
python hotel_reservation_fastapi.py
```

**Output ที่คาดหวัง:**
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete
```

✅ Server กำลังรุนที่ port 8001

---

## ⚙️ ขั้นตอนที่ 3: ตั้งค่า Claude Desktop

### Step 3.1: เปิดไฟล์ Config

**macOS:**
```bash
open ~/Library/Application\ Support/Claude/
```

**Windows:**
```bash
explorer %APPDATA%\Claude\
```

**Linux:**
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

### Step 3.2: แก้ไขไฟล์ `claude_desktop_config.json`

เพิ่มเนื้อหา:
```json
{
  "mcpServers": {
    "hotel-reservation": {
      "command": "python",
      "args": ["/full/path/to/hotel_reservation_mcp_server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

⚠️ **แก้ไข `/full/path/to/` ให้ชี้ไปยังไฟล์จริง**

### Step 3.3: รีสตาร์ท Claude Desktop
- ปิด Claude Desktop
- เปิด Claude Desktop ใหม่

✅ เตรียมพร้อม!

---

## 🔐 ล็อกอินและเริ่มใช้

### ข้อมูลการเข้าสู่ระบบ

| บทบาท | Username | Password |
|------|----------|----------|
| 👥 Guest | guest1 | password123 |
| 👔 Frontdesk | frontdesk1 | password123 |
| 👨‍💼 Manager | manager1 | password123 |
| 💰 Finance | finance1 | password123 |

### เริ่มในการแชท

**ตัวอย่าง 1: ผู้เข้าพัก (Guest)**
```
You: "Login with username guest1 and password password123"
Claude: [Authenticates and returns user info]

You: "Show available rooms from March 15 to March 20"
Claude: [Displays available rooms]

You: "Book room 1 for John Doe, 2 guests"
Claude: [Creates reservation]
```

**ตัวอย่าง 2: พนักงานต้อนรับ (Frontdesk)**
```
You: "Login as frontdesk1"
Claude: [Authenticates]

You: "Show all rooms"
Claude: [Lists all rooms with status]

You: "Check in guest for reservation 1"
Claude: [Validates and checks in]
```

**ตัวอย่าง 3: ผู้จัดการ (Manager)**
```
You: "Login as manager1"
Claude: [Authenticates]

You: "Show dashboard statistics"
Claude: [Displays occupancy, revenue, etc.]

You: "Add new suite room 305, floor 3, price 300"
Claude: [Creates new room]
```

**ตัวอย่าง 4: พนักงานการเงิน (Finance)**
```
You: "Login as finance1"
Claude: [Authenticates]

You: "Generate income report"
Claude: [Shows income analysis]

You: "Apply 10% discount to reservation 1"
Claude: [Calculates discount]
```

---

## 📋 ไป Tools ที่สำคัญ

### 👥 Guest Tools
- 🔍 `search_available_rooms` - ค้นหาห้องว่าง
- 📅 `create_reservation` - สร้างการจอง
- ❌ `cancel_reservation` - ยกเลิกการจอง
- 💳 `make_payment` - ชำระเงิน
- 🧾 `generate_invoice` - สร้างใบเสร็จ

### 👔 Frontdesk Tools
- 🏨 `get_all_rooms` - ดูห้องทั้งหมด
- 🔧 `update_room_status` - อัปเดตสถานะ
- 🔑 `check_in` - เช็คอิน
- 🚪 `check_out` - เช็คเอาท์
- 🔄 `change_room` - เปลี่ยนห้อง

### 👨‍💼 Manager Tools
- 📊 `get_dashboard_statistics` - ดูสถิติ
- 📋 `view_all_reservations` - ดูการจองทั้งหมด
- ➕ `create_room` - สร้างห้อง
- 🗑️ `delete_room` - ลบห้อง

### 💰 Finance Tools
- 💰 `view_all_payments` - ดูการชำระเงิน
- 📊 `get_income_report` - รายงานรายได้
- 🏷️ `apply_discount` - ใช้ส่วนลด
- ⚠️ `apply_penalty_fee` - เก็บค่าปรับ

---

## 🧪 ทดสอบ API โดยตรง

### Health Check
```bash
curl http://127.0.0.1:8001/health
```

### Login
```bash
curl -X POST http://127.0.0.1:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"guest1", "password":"password123"}'
```

### API Documentation
```
Open in browser: http://127.0.0.1:8001/docs
```

---

## ✨ สิ่งที่ได้รับ

✅ **FastAPI Server** - `hotel_reservation_fastapi.py`
- 25+ endpoints
- JWT authentication
- Role-based access control
- Mock database

✅ **MCP Server** - `hotel_reservation_mcp_server.py`
- Integrates with Claude
- Wraps FastAPI API
- Token management

✅ **Documentation**
- `README_HOTEL.md` - Complete guide
- `HOTEL_GUIDE.py` - Use cases & examples
- `QUICKSTART_HOTEL.md` - This file

✅ **Configuration**
- `requirements_hotel.txt` - Dependencies
- `claude_config_hotel.json` - Claude Desktop config

---

## 🎯 Use Cases ทั้งหมด

### ✅ Diagram 1: Guest Use Cases
- Search Availability
- Create Reservation (includes Payment & Login)
- Cancel Reservation (extends Penalty Fee)

### ✅ Diagram 2: All Roles
- Check-In (with Validation)
- Check-Out (includes Generate Invoice)
- Change Room (includes Search Availability)
- Update Income (Financial Reports)
- Apply Penalties & Discounts
- View Statistics & Dashboards

---

## 🔒 Security Features

✅ JWT-based authentication
✅ Role-based authorization
✅ Protected endpoints
✅ Token expiration (24 hours)
✅ Password validation

---

## 🚨 Troubleshooting

### ❌ "Port 8001 already in use"
แก้ไขไฟล์ `hotel_reservation_fastapi.py`:
```python
# ค้นหา: uvicorn.run(app, host="127.0.0.1", port=8001)
# เปลี่ยนเป็น:
uvicorn.run(app, host="127.0.0.1", port=8002)
```
แล้ว update `API_BASE_URL` ใน `hotel_reservation_mcp_server.py`

### ❌ "Tools ไม่ปรากฏ"
1. ตรวจสอบว่า FastAPI กำลังรัน
2. ตรวจสอบ config path ถูกต้อง
3. รีสตาร์ท Claude Desktop
4. ตรวจสอบหมายเลข port ถูกต้อง

### ❌ "Authentication failed"
ตรวจสอบ username และ password:
- guest1 / password123
- frontdesk1 / password123
- manager1 / password123
- finance1 / password123

---

## 📚 ข้อมูลเพิ่มเติม

อ่าน:
- `README_HOTEL.md` - Complete documentation
- `HOTEL_GUIDE.py` - Detailed examples & architecture
- ไฟล์ Python comments - Code documentation

---

## 🎉 Ready to Start!

1. ✅ ติดตั้ง dependencies
2. ✅ รัน FastAPI server
3. ✅ ตั้งค่า Claude Desktop
4. ✅ รีสตาร์ท Claude
5. ✅ เริ่มใช้งาน!

**ลองสั่ง:**
```
"Login with username guest1 and password password123"
```

Enjoy! 🏨✨
