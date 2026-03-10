# 🚀 Hotel Reservation System - Windows Installation Guide

## ✅ แก้ไขแล้ว: MCP Version

ปัญหา: `mcp==0.1.8` ไม่มีในฐานข้อมูลแล้ว  
วิธีแก้: ใช้เวอร์ชันล่าสุด `mcp==1.26.0`

---

## 📋 ขั้นตอนการติดตั้งบน Windows

### ✅ ขั้นตอนที่ 1: สร้าง Virtual Environment

```bash
# เปิด PowerShell ที่ project folder
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate
```

**คุณจะเห็น: `(.venv) PS D:\oop-project>`**

---

### ✅ ขั้นตอนที่ 2: ติดตั้ง Dependencies

```bash
# Upgrade pip ก่อน (recommended)
python -m pip install --upgrade pip

# ติดตั้ง requirements
pip install -r requirements_hotel.txt
```

**Expected output:**
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 httpx-0.25.2 ...
```

---

### ✅ ขั้นตอนที่ 3: ยืนยันการติดตั้ง

```bash
# ตรวจสอบว่า packages ติดตั้งเรียบร้อย
pip list | findstr "fastapi uvicorn httpx mcp"
```

**ควรแสดง:**
```
fastapi               0.104.1
httpx                 0.25.2
mcp                   1.26.0
pydantic              2.5.2
pyjwt                 2.8.1
uvicorn               0.24.0
```

---

## 🏃 รันระบบ

### Terminal 1: รัน FastAPI Server

```bash
# Make sure virtual environment is activated
(.venv) PS D:\oop-project> python hotel_reservation_fastapi.py
```

**Output ที่คาดหวัง:**
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete
```

✅ **Server กำลังรัน!**

---

### Browser: ทดสอบ FastAPI

เปิด: `http://127.0.0.1:8001/docs`

จะเห็น Swagger UI พร้อมทุก endpoints

---

## 🖼️ ตั้งค่า Claude Desktop

### ขั้นตอนที่ 1: หาไฟล์ config

**Windows:**
```powershell
# คำสั่งหาไฟล์
explorer %APPDATA%\Claude\
```

หรือเปิดด้วยตนเอง:
```
C:\Users\<YourUsername>\AppData\Roaming\Claude\
```

### ขั้นตอนที่ 2: แก้ไข `claude_desktop_config.json`

ใช้ Notepad หรือ VSCode เปิดไฟล์:

```json
{
  "mcpServers": {
    "hotel-reservation": {
      "command": "python",
      "args": ["D:\\oop-project\\hotel_reservation_mcp_server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

⚠️ **แทน `D:\\oop-project\\` ด้วย path จริงของคุณ**

### ขั้นตอนที่ 3: รีสตาร์ท Claude Desktop

1. ปิด Claude Desktop ทั้งหมด
2. เปิด Claude Desktop ใหม่

✅ **MCP Server ตั้งค่าเสร็จ!**

---

## 🔐 ล็อกอินและทดสอบ

### ทดสอบใน Claude:

```
You: "Login with username guest1 and password password123"
Claude: [Returns user information with token]

You: "Show available rooms from March 15 to March 20"
Claude: [Shows available rooms]

You: "Book room 1 for John Doe, 2 guests"
Claude: [Creates reservation]
```

---

## 📋 Login Credentials

| Role | Username | Password |
|------|----------|----------|
| 👥 Guest | guest1 | password123 |
| 👔 Frontdesk | frontdesk1 | password123 |
| 👨‍💼 Manager | manager1 | password123 |
| 💰 Finance | finance1 | password123 |

---

## 🐛 Troubleshooting

### ❌ "mcp not found" หรือ import error

```bash
# ตรวจสอบว่า virtual environment เปิดอยู่
# ควรเห็น (.venv) ใน PowerShell

# ถ้าไม่เห็น ให้รัน:
.venv\Scripts\activate

# แล้วลองติดตั้งใหม่:
pip install -r requirements_hotel.txt
```

### ❌ Port 8001 already in use

```bash
# หา process ที่ใช้ port 8001
netstat -ano | findstr :8001

# Kill process:
taskkill /PID <PID> /F

# หรือแก้ port ใน hotel_reservation_fastapi.py:
# ค้นหา: uvicorn.run(app, host="127.0.0.1", port=8001)
# เปลี่ยนเป็น: uvicorn.run(app, host="127.0.0.1", port=8002)
```

### ❌ Claude tools ไม่ปรากฏ

1. ตรวจสอบ FastAPI กำลังรัน
2. ตรวจสอบ config path ถูกต้อง (ต้องใช้ full path)
3. รีสตาร์ท Claude
4. ตรวจสอบ PowerShell logs ใน Claude

---

## ✨ คำสั่งที่มีประโยชน์

```bash
# List all installed packages
pip list

# Check specific package
pip show mcp

# Upgrade pip
python -m pip install --upgrade pip

# Deactivate virtual environment
deactivate

# Reactivate virtual environment
.venv\Scripts\activate

# Test health check
curl http://127.0.0.1:8001/health
```

---

## 📁 File Locations

```
D:\oop-project\
├── .venv\                          ← Virtual environment
├── hotel_reservation_fastapi.py    ← FastAPI server (MAIN)
├── hotel_reservation_mcp_server.py ← MCP server
├── requirements_hotel.txt          ← Dependencies
├── QUICKSTART_HOTEL.md
├── README_HOTEL.md
└── SUMMARY.md
```

---

## 🎯 Next Steps

1. ✅ ติดตั้ง dependencies
2. ✅ รัน FastAPI server
3. ✅ ตั้งค่า Claude Desktop
4. ✅ รีสตาร์ท Claude
5. ✅ ลองใช้ในการแชท

---

## 💡 Important Notes

✅ **Virtual Environment**: ต้อง activate ทุกครั้งก่อนใช้  
✅ **Port 8001**: FastAPI ใช้ port นี้ (ต้องว่าง)  
✅ **Python Path**: ใน config ต้องเป็น full path (เช่น `D:\\...`)  
✅ **Token**: ใช้ได้ 24 ชั่วโมง (ล็อกอินใหม่หลังหมดอายุ)  

---

**ตอนนี้พร้อมใช้งาน! 🏨✨**

หากมีปัญหา ให้อ้างอิง QUICKSTART_HOTEL.md หรือ README_HOTEL.md
