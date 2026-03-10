# 🏨 Hotel Reservation System - Full Implementation

ระบบจองโรงแรมแบบสมบูรณ์พร้อม MCP Server, Authentication, และ Role-based Access Control

## 📊 Features

### ✨ Complete Implementation
- ✅ JWT Authentication
- ✅ Role-based Access Control (RBAC)
- ✅ 4 User Types: Guest, Frontdesk, Manager, Finance
- ✅ 25+ API Endpoints
- ✅ All use cases from your diagrams implemented

### 👥 User Roles & Permissions

#### 👥 Guest (ผู้เข้าพัก)
- 🔍 Search available rooms
- 📅 Create reservation
- 📋 View my reservations
- 📄 View reservation details
- ❌ Cancel reservation (with penalty fee)
- 💳 Make payment
- 🧾 Generate invoice

#### 👔 Frontdesk Staff (พนักงานต้อนรับ)
- 🏨 View all rooms
- 🔧 Update room status
- 🔑 Check-in guests (with validation)
- 🚪 Check-out guests (with invoice generation)
- 🔄 Change guest room
- 📅 Create reservation for guests
- 💳 Process payments

#### 👨‍💼 Hotel Manager (ผู้จัดการ)
- 📊 Dashboard statistics
- 📋 View all reservations
- ➕ Add new rooms
- 🗑️ Delete rooms
- 🏷️ Apply discounts
- ⚠️ Apply penalty fees
- 📈 View financial reports

#### 💰 Finance Staff (พนักงานการเงิน)
- 💰 View all payments
- 📋 View all invoices
- 📊 Income report
- 🏷️ Apply discounts
- ⚠️ Apply penalty fees
- 💵 Manage payments

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements_hotel.txt
```

### 2. Start FastAPI Server (Terminal 1)
```bash
python hotel_reservation_fastapi.py
```

Output:
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete
```

### 3. Configure Claude Desktop

Edit your Claude Desktop config file:

**macOS:**
```bash
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
notepad %APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

Add this content (update path accordingly):
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

### 4. Restart Claude Desktop
Close and reopen Claude Desktop

### 5. Start Using! 🎉

---

## 🔐 Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Guest | guest1 | password123 |
| Frontdesk | frontdesk1 | password123 |
| Manager | manager1 | password123 |
| Finance | finance1 | password123 |

---

## 💬 Usage Examples

### Guest - Search & Book a Room
```
You: "I want to book a room. I'm a guest, so login me with username guest1"
Claude: [Logs in, returns token]

You: "Search available rooms from March 15 to March 20"
Claude: [Shows available rooms]

You: "Book room 1 for John Doe for 2 guests"
Claude: [Creates reservation]

You: "Make payment of 600 using credit card"
Claude: [Processes payment]

You: "Generate an invoice for my reservation"
Claude: [Creates invoice]
```

### Frontdesk - Check-in Process
```
You: "Login as frontdesk staff with username frontdesk1"
Claude: [Logs in]

You: "Guest is arriving, check in reservation 1"
Claude: [Validates date, updates status]

You: "Update room 1 status to occupied"
Claude: [Updates room status]
```

### Manager - Dashboard
```
You: "Login as manager with username manager1"
Claude: [Logs in]

You: "Show me dashboard statistics"
Claude: [Shows occupancy, revenue, reservations, etc.]

You: "Show all reservations"
Claude: [Lists all reservations with status]

You: "Add a new deluxe room, number 305, floor 3, price 300"
Claude: [Creates new room]
```

### Finance - Income Report
```
You: "Login as finance with username finance1"
Claude: [Logs in]

You: "Generate income report"
Claude: [Shows total income, by room type, payments, etc.]

You: "Apply 10% discount to reservation 1"
Claude: [Calculates discount amount]

You: "Apply 10% penalty fee for cancelled reservation"
Claude: [Calculates penalty]
```

---

## 🏗️ Architecture

```
┌─────────────────┐
│   Claude        │
│   (User)        │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────────────────────┐
│   MCP Server                    │
│ (hotel_reservation_mcp_server)  │
│ - list_tools()                  │
│ - call_tool()                   │
│ - _call_api()                   │
└────────┬────────────────────────┘
         │ HTTP Requests
         ▼
┌─────────────────────────────────┐
│   FastAPI Server                │
│ (hotel_reservation_fastapi)     │
│ - Authentication (JWT)          │
│ - 25+ Endpoints                 │
│ - Role-based Access Control     │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Mock Database (In-Memory)     │
│ - users_db                      │
│ - rooms_db                      │
│ - reservations_db               │
│ - payments_db                   │
│ - invoices_db                   │
│ - discounts_db                  │
└─────────────────────────────────┘
```

---

## 📋 API Endpoints (25+)

### Authentication
- `POST /auth/login` - Login
- `GET /auth/me` - Get current user

### Guest Operations
- `GET /rooms/available` - Search rooms
- `POST /reservations` - Create reservation
- `GET /reservations` - Get my reservations
- `GET /reservations/{id}` - View details
- `DELETE /reservations/{id}` - Cancel reservation
- `POST /payments` - Make payment
- `POST /invoices` - Generate invoice

### Frontdesk Operations
- `GET /rooms` - View all rooms
- `PUT /rooms/{id}/status` - Update room status
- `POST /check-in` - Check-in guest
- `POST /check-out` - Check-out guest
- `POST /change-room` - Change guest room

### Manager Operations
- `GET /reservations-all` - View all reservations
- `GET /dashboard/statistics` - Dashboard stats
- `POST /rooms` - Create new room
- `DELETE /rooms/{id}` - Delete room

### Finance Operations
- `GET /payments-all` - View all payments
- `GET /invoices-all` - View all invoices
- `GET /finance/income-report` - Income report
- `POST /apply-discount` - Apply discount
- `POST /apply-penalty-fee` - Apply penalty

### Health
- `GET /health` - Health check

---

## 📊 Database Schema

### Users
```
{
  "id": 1,
  "username": "guest1",
  "email": "guest1@email.com",
  "full_name": "John Doe",
  "role": "guest"
}
```

### Rooms
```
{
  "id": 1,
  "room_number": "101",
  "floor": 1,
  "room_type": "standard",
  "price_per_night": 100,
  "capacity": 2,
  "status": "available"
}
```

### Reservations
```
{
  "id": 1,
  "guest_name": "John Doe",
  "room_id": 1,
  "check_in": "2024-03-15",
  "check_out": "2024-03-20",
  "status": "confirmed",
  "total_price": 600
}
```

---

## 🧪 Testing

### API Documentation
```
Open in browser: http://127.0.0.1:8001/docs
```

### Manual Testing with curl
```bash
# Health check
curl http://127.0.0.1:8001/health

# Login
curl -X POST http://127.0.0.1:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"guest1", "password":"password123"}'

# Get current user (with token)
TOKEN="<token from login>"
curl http://127.0.0.1:8001/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔄 Use Cases from Your Diagrams

### Diagram 1: Guest Use Cases
✅ Create Reservation
  - Includes: Search Availability
  - Includes: Payment
  - Includes: Login

✅ Cancel Reservation
  - Includes: Login
  - Extends: Apply Penalty Fee

### Diagram 2: Complete System
✅ Check-In (Frontdesk)
  - Includes: Validation

✅ Check-Out (Frontdesk)
  - Extends: Generate Invoice
  - Includes: Check-In

✅ Change Room (Frontdesk)
  - Includes: Search Availability

✅ View Income (Finance)
  - Includes: Update Income

✅ Apply Penalties
✅ Apply Discounts
✅ And many more...

---

## 🎯 Key Features Implemented

| Feature | Implementation |
|---------|-----------------|
| **Authentication** | JWT-based login |
| **Authorization** | Role-based access control |
| **Guest Features** | Search, Book, Pay, Cancel |
| **Frontdesk Features** | Check-in/out, Room management |
| **Manager Features** | Dashboard, Room CRUD, Discounts |
| **Finance Features** | Payments, Invoices, Reports |
| **Includes/Extends** | Use case relationships mapped |
| **Error Handling** | Proper HTTP status codes |
| **Validation** | Date validation, permission checks |
| **Mock Database** | In-memory storage |

---

## 📝 File Structure

```
hotel-reservation/
├── hotel_reservation_fastapi.py      ← FastAPI Server (Main API)
├── hotel_reservation_mcp_server.py   ← MCP Server (Claude Integration)
├── HOTEL_GUIDE.py                    ← Complete Usage Guide
├── requirements_hotel.txt             ← Dependencies
├── claude_config_hotel.json           ← Claude Desktop Config
└── README.md                          ← This file
```

---

## 🚨 Troubleshooting

### Port Already in Use
```bash
# Change port in hotel_reservation_fastapi.py
# Find: uvicorn.run(app, host="127.0.0.1", port=8001)
# Change port=8001 to port=8002 (or any free port)
# Then update API_BASE_URL in mcp_server.py
```

### Token Expired
```
Login again with your username and password
```

### Permission Denied
```
Make sure you're using the correct user role
- Guests can only access guest features
- Frontdesk staff can access frontdesk features
- etc.
```

### Claude Not Showing Tools
1. Verify FastAPI server is running
2. Verify config path is correct
3. Restart Claude Desktop
4. Check that Python path in config is correct

---

## 🎓 Learning Resources

Read HOTEL_GUIDE.py for:
- Detailed use case examples
- All available tools
- Role-based permissions
- Database schema
- And more!

---

## 📞 Support

For issues:
1. Check HOTEL_GUIDE.py
2. Verify FastAPI is running
3. Check Claude Desktop logs
4. Ensure correct credentials

---

**Happy booking! 🏨✨**
