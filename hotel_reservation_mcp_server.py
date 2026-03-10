"""
Hotel Reservation System - MCP Server
Wrap FastAPI Hotel Reservation API พร้อม Role-based Access Control
"""

import asyncio
import httpx
import json
from typing import Any, Optional
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ToolResult
import mcp.server.stdio
import mcp.types as types

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

API_BASE_URL = "http://127.0.0.1:8001"
REQUEST_TIMEOUT = 10.0

# ═══════════════════════════════════════════════════════════════════════════════
# MCP Server Class
# ═══════════════════════════════════════════════════════════════════════════════

class HotelReservationServer:
    def __init__(self):
        self.server = mcp.server.stdio.StdioServer(
            name="hotel-reservation",
            version="1.0.0"
        )
        self.access_token: Optional[str] = None
        self.current_user: Optional[dict] = None
        self.current_role: Optional[str] = None
        
        # ลงทะเบียน handlers
        self.server.set_request_handler(types.ListToolsRequest, self.list_tools)
        self.server.set_request_handler(types.CallToolRequest, self.call_tool)
        self.server.set_request_handler(types.InitializeRequest, self.initialize)

    async def initialize(self, request: types.InitializeRequest) -> types.InitializeResult:
        """Initialize the MCP server"""
        print("🚀 Initializing Hotel Reservation MCP Server...", flush=True)
        return types.InitializeResult(
            protocolVersion="2024-11-05",
            capabilities=types.ServerCapabilities(tools=types.ToolsCapability(listChanged=False)),
            serverInfo=types.Implementation(
                name="hotel-reservation-server",
                version="1.0.0"
            )
        )

    async def list_tools(self, request: types.ListToolsRequest) -> types.ListToolsResult:
        """ส่งรายชื่อ tools"""
        tools = [
            # ═══════════════════════════════════════════════════════════════════════
            # Authentication Tools
            # ═══════════════════════════════════════════════════════════════════════
            
            Tool(
                name="login",
                description="""🔐 ล็อกอินเข้าระบบ
                
Users:
- guest1 (Guest) 
- frontdesk1 (Frontdesk Staff)
- manager1 (Hotel Manager)
- finance1 (Finance Staff)
Password: password123 (สำหรับทั้งหมด)""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Username (guest1, frontdesk1, manager1, finance1)"
                        },
                        "password": {
                            "type": "string",
                            "description": "Password (password123)"
                        }
                    },
                    "required": ["username", "password"]
                }
            ),
            
            Tool(
                name="get_current_user",
                description="📋 ดูข้อมูลผู้ใช้ปัจจุบัน (Get Current User)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            
            # ═══════════════════════════════════════════════════════════════════════
            # Guest Tools - Search & Booking
            # ═══════════════════════════════════════════════════════════════════════
            
            Tool(
                name="search_available_rooms",
                description="🔍 Guest: ค้นหาห้องว่าง (Search Availability)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "check_in": {
                            "type": "string",
                            "description": "วันเข้าพัก (YYYY-MM-DD)"
                        },
                        "check_out": {
                            "type": "string",
                            "description": "วันออกพัก (YYYY-MM-DD)"
                        }
                    },
                    "required": ["check_in", "check_out"]
                }
            ),
            
            Tool(
                name="create_reservation",
                description="📅 Guest/Frontdesk: สร้างการจอง (Create Reservation)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guest_name": {
                            "type": "string",
                            "description": "ชื่อผู้เข้าพัก"
                        },
                        "room_id": {
                            "type": "integer",
                            "description": "ID ของห้อง"
                        },
                        "check_in": {
                            "type": "string",
                            "description": "วันเข้าพัก (YYYY-MM-DD)"
                        },
                        "check_out": {
                            "type": "string",
                            "description": "วันออกพัก (YYYY-MM-DD)"
                        },
                        "number_of_guests": {
                            "type": "integer",
                            "description": "จำนวนผู้เข้าพัก"
                        },
                        "special_requests": {
                            "type": "string",
                            "description": "คำขอพิเศษ (ไม่บังคับ)"
                        }
                    },
                    "required": ["guest_name", "room_id", "check_in", "check_out", "number_of_guests"]
                }
            ),
            
            Tool(
                name="get_my_reservations",
                description="📋 Guest: ดูการจองของฉัน (View My Reservations)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            
            Tool(
                name="get_reservation",
                description="📄 ดูรายละเอียดการจอง (View Reservation Details)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "integer",
                            "description": "ID ของการจอง"
                        }
                    },
                    "required": ["reservation_id"]
                }
            ),
            
            Tool(
                name="cancel_reservation",
                description="❌ Guest: ยกเลิกการจอง (Cancel Reservation) ⚠️ มีค่าปรับ",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "integer",
                            "description": "ID ของการจองที่ต้องการยกเลิก"
                        }
                    },
                    "required": ["reservation_id"]
                }
            ),
            
            # ═══════════════════════════════════════════════════════════════════════
            # Payment & Invoice
            # ═══════════════════════════════════════════════════════════════════════
            
            Tool(
                name="make_payment",
                description="💳 Guest/Frontdesk: ชำระเงิน (Make Payment)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "integer",
                            "description": "ID ของการจอง"
                        },
                        "amount": {
                            "type": "number",
                            "description": "จำนวนเงิน"
                        },
                        "payment_method": {
                            "type": "string",
                            "description": "วิธีการชำระ (cash, credit_card, bank_transfer)"
                        }
                    },
                    "required": ["reservation_id", "amount", "payment_method"]
                }
            ),
            
            Tool(
                name="generate_invoice",
                description="🧾 Guest/Frontdesk: สร้างใบเสร็จ (Generate Invoice)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "integer",
                            "description": "ID ของการจอง"
                        }
                    },
                    "required": ["reservation_id"]
                }
            ),
            
            # ═══════════════════════════════════════════════════════════════════════
            # Frontdesk Tools
            # ═══════════════════════════════════════════════════════════════════════
            
            Tool(
                name="get_all_rooms",
                description="🏨 Frontdesk: ดูห้องทั้งหมด (View All Rooms)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            
            Tool(
                name="update_room_status",
                description="🔧 Frontdesk: อัปเดตสถานะห้อง (Update Room Status)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "room_id": {
                            "type": "integer",
                            "description": "ID ของห้อง"
                        },
                        "new_status": {
                            "type": "string",
                            "description": "สถานะใหม่ (available, occupied, maintenance, reserved)"
                        }
                    },
                    "required": ["room_id", "new_status"]
                }
            ),
            
            Tool(
                name="check_in",
                description="🔑 Frontdesk: เช็คอิน (Check-In) ✅ Includes Validation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "integer",
                            "description": "ID ของการจอง"
                        }
                    },
                    "required": ["reservation_id"]
                }
            ),
            
            Tool(
                name="check_out",
                description="🚪 Frontdesk: เช็คเอาท์ (Check-Out) ✅ Includes Invoice",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "integer",
                            "description": "ID ของการจอง"
                        }
                    },
                    "required": ["reservation_id"]
                }
            ),
            
            Tool(
                name="change_room",
                description="🔄 Frontdesk: เปลี่ยนห้อง (Change Room)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "integer",
                            "description": "ID ของการจอง"
                        },
                        "new_room_id": {
                            "type": "integer",
                            "description": "ID ของห้องใหม่"
                        }
                    },
                    "required": ["reservation_id", "new_room_id"]
                }
            ),
            
            # ═══════════════════════════════════════════════════════════════════════
            # Manager Tools
            # ═══════════════════════════════════════════════════════════════════════
            
            Tool(
                name="view_all_reservations",
                description="📊 Manager: ดูการจองทั้งหมด (View All Reservations)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            
            Tool(
                name="get_dashboard_statistics",
                description="📈 Manager: ดูสถิติและรายงาน (Dashboard Statistics)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            
            Tool(
                name="create_room",
                description="➕ Manager: สร้างห้องใหม่ (Add New Room)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "room_number": {
                            "type": "string",
                            "description": "หมายเลขห้อง (เช่น 101, 201)"
                        },
                        "floor": {
                            "type": "integer",
                            "description": "ชั้น"
                        },
                        "room_type": {
                            "type": "string",
                            "description": "ประเภทห้อง (standard, deluxe, suite)"
                        },
                        "price_per_night": {
                            "type": "number",
                            "description": "ราคาต่อคืน"
                        },
                        "capacity": {
                            "type": "integer",
                            "description": "ความจุ (จำนวนคน)"
                        },
                        "description": {
                            "type": "string",
                            "description": "คำอธิบาย (ไม่บังคับ)"
                        }
                    },
                    "required": ["room_number", "floor", "room_type", "price_per_night", "capacity"]
                }
            ),
            
            Tool(
                name="delete_room",
                description="🗑️ Manager: ลบห้อง (Delete Room)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "room_id": {
                            "type": "integer",
                            "description": "ID ของห้อง"
                        }
                    },
                    "required": ["room_id"]
                }
            ),
            
            # ═══════════════════════════════════════════════════════════════════════
            # Finance Tools
            # ═══════════════════════════════════════════════════════════════════════
            
            Tool(
                name="view_all_payments",
                description="💰 Finance: ดูการชำระเงินทั้งหมด (View All Payments)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            
            Tool(
                name="view_all_invoices",
                description="📋 Finance: ดูใบเสร็จทั้งหมด (View All Invoices)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            
            Tool(
                name="get_income_report",
                description="📊 Finance: รายงานรายได้ (Income Report) ✅ Includes Update Income",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            
            Tool(
                name="apply_discount",
                description="🏷️ Finance: ใช้ส่วนลด (Apply Discount)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "integer",
                            "description": "ID ของการจอง"
                        },
                        "discount_id": {
                            "type": "integer",
                            "description": "ID ของส่วนลด"
                        }
                    },
                    "required": ["reservation_id", "discount_id"]
                }
            ),
            
            Tool(
                name="apply_penalty_fee",
                description="⚠️ Finance: เก็บค่าปรับ (Apply Penalty Fee)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reservation_id": {
                            "type": "integer",
                            "description": "ID ของการจอง"
                        },
                        "penalty_percentage": {
                            "type": "number",
                            "description": "เปอร์เซ็นต์ค่าปรับ (default: 10.0)"
                        }
                    },
                    "required": ["reservation_id"]
                }
            ),
        ]
        
        return types.ListToolsResult(tools=tools)

    async def call_tool(self, request: types.CallToolRequest) -> types.CallToolResult:
        """ส่งคำขอไปยัง FastAPI"""
        tool_name = request.name
        arguments = request.arguments
        
        try:
            result = await self._call_api(tool_name, arguments)
            
            return types.CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2)
                    )
                ]
            )
        
        except Exception as e:
            error_message = f"❌ เกิดข้อผิดพลาด: {str(e)}"
            print(error_message, flush=True)
            return types.CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=error_message
                    )
                ],
                isError=True
            )

    async def _call_api(self, tool_name: str, arguments: dict) -> Any:
        """เรียก FastAPI API"""
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            
            # ═══════════════════════════════════════════════════════════════════════
            # Authentication
            # ═══════════════════════════════════════════════════════════════════════
            
            if tool_name == "login":
                response = await client.post(
                    f"{API_BASE_URL}/auth/login",
                    json={
                        "username": arguments["username"],
                        "password": arguments["password"]
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # บันทึก token
                self.access_token = data["access_token"]
                self.current_user = data["user"]
                self.current_role = data["role"]
                
                return data
            
            elif tool_name == "get_current_user":
                if not self.access_token:
                    raise Exception("Not logged in. Please login first.")
                
                response = await client.get(
                    f"{API_BASE_URL}/auth/me",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            # ═══════════════════════════════════════════════════════════════════════
            # Guest Tools
            # ═══════════════════════════════════════════════════════════════════════
            
            elif tool_name == "search_available_rooms":
                response = await client.get(
                    f"{API_BASE_URL}/rooms/available",
                    params=arguments,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "create_reservation":
                response = await client.post(
                    f"{API_BASE_URL}/reservations",
                    json=arguments,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "get_my_reservations":
                response = await client.get(
                    f"{API_BASE_URL}/reservations",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "get_reservation":
                response = await client.get(
                    f"{API_BASE_URL}/reservations/{arguments['reservation_id']}",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "cancel_reservation":
                response = await client.delete(
                    f"{API_BASE_URL}/reservations/{arguments['reservation_id']}",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            # ═══════════════════════════════════════════════════════════════════════
            # Payment & Invoice
            # ═══════════════════════════════════════════════════════════════════════
            
            elif tool_name == "make_payment":
                response = await client.post(
                    f"{API_BASE_URL}/payments",
                    json=arguments,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "generate_invoice":
                response = await client.post(
                    f"{API_BASE_URL}/invoices",
                    params={"reservation_id": arguments["reservation_id"]},
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            # ═══════════════════════════════════════════════════════════════════════
            # Frontdesk Tools
            # ═══════════════════════════════════════════════════════════════════════
            
            elif tool_name == "get_all_rooms":
                response = await client.get(
                    f"{API_BASE_URL}/rooms",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "update_room_status":
                response = await client.put(
                    f"{API_BASE_URL}/rooms/{arguments['room_id']}/status",
                    params={"new_status": arguments["new_status"]},
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "check_in":
                response = await client.post(
                    f"{API_BASE_URL}/check-in",
                    params={"reservation_id": arguments["reservation_id"]},
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "check_out":
                response = await client.post(
                    f"{API_BASE_URL}/check-out",
                    params={"reservation_id": arguments["reservation_id"]},
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "change_room":
                response = await client.post(
                    f"{API_BASE_URL}/change-room",
                    params=arguments,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            # ═══════════════════════════════════════════════════════════════════════
            # Manager Tools
            # ═══════════════════════════════════════════════════════════════════════
            
            elif tool_name == "view_all_reservations":
                response = await client.get(
                    f"{API_BASE_URL}/reservations-all",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "get_dashboard_statistics":
                response = await client.get(
                    f"{API_BASE_URL}/dashboard/statistics",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "create_room":
                response = await client.post(
                    f"{API_BASE_URL}/rooms",
                    json=arguments,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "delete_room":
                response = await client.delete(
                    f"{API_BASE_URL}/rooms/{arguments['room_id']}",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            # ═══════════════════════════════════════════════════════════════════════
            # Finance Tools
            # ═══════════════════════════════════════════════════════════════════════
            
            elif tool_name == "view_all_payments":
                response = await client.get(
                    f"{API_BASE_URL}/payments-all",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "view_all_invoices":
                response = await client.get(
                    f"{API_BASE_URL}/invoices-all",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "get_income_report":
                response = await client.get(
                    f"{API_BASE_URL}/finance/income-report",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "apply_discount":
                response = await client.post(
                    f"{API_BASE_URL}/apply-discount",
                    params=arguments,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            elif tool_name == "apply_penalty_fee":
                response = await client.post(
                    f"{API_BASE_URL}/apply-penalty-fee",
                    params=arguments,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                return response.json()
            
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

    async def run(self):
        """รัน MCP Server"""
        async with self.server:
            print("✅ Hotel Reservation MCP Server is running...", flush=True)
            await self.server.wait_for_exit()

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    server = HotelReservationServer()
    asyncio.run(server.run())
