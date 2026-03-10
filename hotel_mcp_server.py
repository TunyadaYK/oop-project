"""
Hotel MCP Server — hotel_mcp_server.py
=======================================
MCP (Model Context Protocol) Server ที่ wrap FastAPI Hotel Reservation System
ทำให้ Claude หรือ AI Agent อื่นๆ สามารถเรียกใช้ API ได้โดยตรง

วิธีรัน:
    1. รัน FastAPI ก่อน:
       uvicorn main:app --reload --port 8000

    2. รัน MCP Server (อีก terminal):
       python hotel_mcp_server.py

    หรือรันพร้อมกันด้วย:
       python hotel_mcp_server.py --with-fastapi

ติดตั้ง dependency:
    pip install mcp httpx fastapi uvicorn
"""

import asyncio
import httpx
import json
import subprocess
import sys
from typing import Any
from datetime import datetime, timedelta

# ── MCP SDK Import ──────────────────────────────────────────────
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

# ══════════════════════════════════════════════════════════════
#  Config — เปลี่ยน BASE_URL ถ้ารัน FastAPI port อื่น
# ══════════════════════════════════════════════════════════════

BASE_URL = "http://127.0.0.1:8000"

MCP_TOKEN = "MCP-INTERNAL-TOKEN"

# ══════════════════════════════════════════════════════════════
#  HTTP Helper — ใช้ httpx เรียก FastAPI
# ══════════════════════════════════════════════════════════════

async def call_api(
    method: str,
    path: str,
    params: dict = None,
    body: dict = None,
) -> dict:
    """
    Helper กลางสำหรับเรียก FastAPI ทุก endpoint
    - method: "GET" | "POST"
    - path:   "/guests", "/reservations/{id}/confirm" ฯลฯ
    - params: query string dict
    - body:   JSON body dict
    """
    # ดึง token จาก server context (ถ้า login มาแล้ว) หรือใช้ MCP_TOKEN
    auth_token = getattr(server, "context", {}).get("auth_token", MCP_TOKEN)
    
    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as client:
        url = f"{BASE_URL}{path}"
        try:
            if method.upper() == "GET":
                resp = await client.get(url, params=params)
            else:  # POST / PUT / PATCH
                resp = await client.post(url, params=params, json=body)

            # พยายาม parse JSON เสมอ
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}

            # ถ้า status code ไม่ใช่ 2xx ให้ wrap error
            if resp.status_code >= 400:
                return {
                    "error": True,
                    "status_code": resp.status_code,
                    "detail": data,
                }
            return data

        except httpx.ConnectError:
            return {
                "error": True,
                "detail": f"ไม่สามารถเชื่อมต่อ FastAPI ที่ {BASE_URL} ได้ — กรุณารัน uvicorn ก่อน",
            }
        except Exception as e:
            return {"error": True, "detail": str(e)}


def fmt(data: Any) -> str:
    """แปลง dict/list เป็น JSON string สวยงาม"""
    return json.dumps(data, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════
#  MCP Server Instance
# ══════════════════════════════════════════════════════════════

server = Server("hotel-reservation-mcp")

# ══════════════════════════════════════════════════════════════
#  1. list_tools — ประกาศ tools ทั้งหมดที่ MCP มี
#     Claude จะเห็น tool เหล่านี้และเลือกเรียกใช้ได้
# ══════════════════════════════════════════════════════════════

# # ตัวอย่าง Python MCP server
# @server.tool("hotel_login")
# async def hotel_login(username: str, password: str):
#     response = await http_client.post("/auth/login", json={
#         "username": username,
#         "password": password
#     })
#     token = response.json()["access_token"]
#     # เก็บ token ไว้ใน session context
#     server.context["auth_token"] = token
#     return {"token": token}

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="hotel_login",
            description="Authenticate user and return JWT access token (calls /auth/login).",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Username"},
                    "password": {"type": "string", "description": "Password"},
                },
                "required": ["username", "password"],
            },
        ),

        # ── Guests ──────────────────────────────────────────
        Tool(
            name="hotel_register_guest",
            description="ลงทะเบียนผู้เข้าพักใหม่ในระบบโรงแรม",
            inputSchema={
                "type": "object",
                "properties": {
                    "name":        {"type": "string", "description": "ชื่อ-นามสกุลผู้เข้าพัก"},
                    "phone":       {"type": "string", "description": "เบอร์โทรศัพท์"},
                    "email":       {"type": "string", "description": "อีเมล"},
                    "id_document": {"type": "string", "description": "เลขบัตรประชาชน/พาสปอร์ต (ไม่บังคับ)", "default": ""},
                },
                "required": ["name", "phone", "email"],
            },
        ),

        Tool(
            name="hotel_list_guests",
            description="ดูรายชื่อผู้เข้าพักทั้งหมดในระบบ พร้อมจำนวน no-show และมัดจำที่ต้องชำระ",
            inputSchema={"type": "object", "properties": {}},
        ),

        Tool(
            name="hotel_get_guest",
            description="ดูข้อมูลผู้เข้าพักรายคน ด้วย guest_id เช่น GST0001",
            inputSchema={
                "type": "object",
                "properties": {
                    "guest_id": {"type": "string", "description": "รหัสผู้เข้าพัก เช่น GST0001"},
                },
                "required": ["guest_id"],
            },
        ),

        # ── Rooms ────────────────────────────────────────────
        Tool(
            name="hotel_list_rooms",
            description="ดูห้องทั้งหมด กรองตาม room_type (STANDARD/DELUXE) หรือ status ได้",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_type": {
                        "type": "string",
                        "enum": ["STANDARD", "DELUXE"],
                        "description": "กรองตามประเภทห้อง (ไม่ใส่ = ทั้งหมด)",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["Available", "Hold", "Occupied", "Cleaning", "Maintenance"],
                        "description": "กรองตามสถานะห้อง",
                    },
                },
            },
        ),

        Tool(
            name="hotel_search_rooms",
            description="ค้นหาห้องว่างตามช่วงวันที่และประเภทห้อง",
            inputSchema={
                "type": "object",
                "properties": {
                    "check_in":  {"type": "string", "description": "วันเช็คอิน ISO format เช่น 2025-07-01T14:00:00"},
                    "check_out": {"type": "string", "description": "วันเช็คเอาท์ ISO format เช่น 2025-07-04T12:00:00"},
                    "room_type": {
                        "type": "string",
                        "enum": ["STANDARD", "DELUXE"],
                        "description": "ประเภทห้องที่ต้องการ (ไม่ใส่ = ทุกประเภท)",
                    },
                },
                "required": ["check_in", "check_out"],
            },
        ),

        Tool(
            name="hotel_update_room_status",
            description="เปลี่ยนสถานะห้อง เช่น ส่งไป Maintenance พร้อมระบุเหตุผล",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_id":    {"type": "string", "description": "รหัสห้อง เช่น RM-0101"},
                    "new_status": {
                        "type": "string",
                        "enum": ["Available", "Hold", "Occupied", "Cleaning", "Maintenance"],
                    },
                    "reason": {"type": "string", "description": "เหตุผล เช่น ท่อแตก", "default": ""},
                },
                "required": ["room_id", "new_status"],
            },
        ),

        # ── Reservations ─────────────────────────────────────
        Tool(
            name="hotel_create_reservation",
            description=(
                "สร้างการจองใหม่ (สถานะ Draft หรือ Hold) "
                "ส่วนลดอัตโนมัติ: EarlyBird 10% (จองล่วงหน้า≥30วัน), "
                "LongStay 12% (≥3คืน), Corporate 8% (ใส่ corporate_code)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "guest_id":       {"type": "string", "description": "รหัสผู้เข้าพัก เช่น GST0001"},
                    "room_id":        {"type": "string", "description": "รหัสห้อง เช่น RM-0101"},
                    "check_in_date":  {"type": "string", "description": "วันเช็คอิน ISO8601 เช่น 2025-08-01T14:00:00"},
                    "check_out_date": {"type": "string", "description": "วันเช็คเอาท์ ISO8601 เช่น 2025-08-04T12:00:00"},
                    "channel": {
                        "type": "string",
                        "enum": ["Web", "Phone", "WalkIn"],
                        "default": "Web",
                    },
                    "extra_bed":      {"type": "boolean", "description": "ต้องการเตียงเสริม 800/คืน", "default": False},
                    "corporate_code": {"type": "string", "description": "รหัสองค์กรสำหรับส่วนลด 8%", "default": ""},
                },
                "required": ["guest_id", "room_id", "check_in_date", "check_out_date"],
            },
        ),

        Tool(
            name="hotel_list_reservations",
            description="ดูรายการจองทั้งหมด กรองตาม status หรือค้นหาตามชื่อแขกได้",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["Draft", "Confirmed", "CheckedIn", "CheckedOut", "Cancelled", "NoShow"],
                        "description": "กรองตามสถานะ (ไม่ใส่ = ทั้งหมด)",
                    },
                    "guest_name": {"type": "string", "description": "ค้นหาตามชื่อแขก"},
                },
            },
        ),

        Tool(
            name="hotel_get_reservation",
            description="ดูรายละเอียดการจอง รวมถึง invoice, นโยบายยกเลิก, ประวัติสถานะ",
            inputSchema={
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string", "description": "เลขการจอง เช่น RSV-20250701-00001"},
                },
                "required": ["reservation_id"],
            },
        ),

        Tool(
            name="hotel_confirm_reservation",
            description=(
                "ยืนยันการจองและชำระมัดจำ (1,000 THB ปกติ / 2,000 THB กรณีมีประวัติ No-show) "
                "รองรับ Card, BankTransfer, QR"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string", "description": "เลขการจอง"},
                    "channel": {
                        "type": "string",
                        "enum": ["Card", "BankTransfer", "QR"],
                        "description": "ช่องทางชำระเงิน",
                    },
                    "card_number":     {"type": "string", "default": "4111111111111111"},
                    "card_expiry":     {"type": "string", "default": "12/28"},
                    "card_cvv":        {"type": "string", "default": "123"},
                    "bank_name":       {"type": "string", "default": "KBank"},
                    "proof_url":       {"type": "string", "default": ""},
                    "wallet_provider": {"type": "string", "default": "PromptPay"},
                },
                "required": ["reservation_id", "channel"],
            },
        ),

        Tool(
            name="hotel_pay_balance",
            description="ชำระยอดที่เหลือทั้งหมด (หลังหักมัดจำ) ก่อน checkout",
            inputSchema={
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                    "channel": {
                        "type": "string",
                        "enum": ["Card", "BankTransfer", "QR"],
                    },
                    "card_number":     {"type": "string", "default": "4111111111111111"},
                    "card_expiry":     {"type": "string", "default": "12/28"},
                    "card_cvv":        {"type": "string", "default": "123"},
                    "bank_name":       {"type": "string", "default": "KBank"},
                    "proof_url":       {"type": "string", "default": ""},
                    "wallet_provider": {"type": "string", "default": "PromptPay"},
                },
                "required": ["reservation_id", "channel"],
            },
        ),

        Tool(
            name="hotel_cancel_reservation",
            description=(
                "ยกเลิกการจอง "
                "ฟรีถ้ายกเลิก ≥ 48 ชม.ก่อน check-in / มีค่าปรับ (ค่าห้องคืนแรก) ถ้าน้อยกว่า"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                    "actor_id":       {"type": "string", "default": "staff_001"},
                },
                "required": ["reservation_id"],
            },
        ),

        Tool(
            name="hotel_check_in",
            description="เช็คอินแขก (ต้อง Confirmed และชำระมัดจำแล้วเท่านั้น)",
            inputSchema={
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                    "actor_id":       {"type": "string", "default": "staff_001"},
                },
                "required": ["reservation_id"],
            },
        ),

        Tool(
            name="hotel_check_out",
            description="เช็คเอาท์แขก ต้องชำระยอดทั้งหมดก่อน ระบบจะสร้าง Cleaning Task อัตโนมัติ",
            inputSchema={
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                    "actor_id":       {"type": "string", "default": "staff_001"},
                },
                "required": ["reservation_id"],
            },
        ),

        Tool(
            name="hotel_mark_no_show",
            description="บันทึก No-show (เรียกได้หลัง 23:00 ของวันเช็คอิน) มีค่าปรับ 2,000 THB",
            inputSchema={
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                    "actor_id":       {"type": "string", "default": "staff_001"},
                },
                "required": ["reservation_id"],
            },
        ),

        # ── Rooms - Cleaning ─────────────────────────────────
        Tool(
            name="hotel_complete_cleaning",
            description="แจ้งทำความสะอาดห้องเสร็จสิ้น ห้องจะกลับมาสถานะ Available",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_id":   {"type": "string", "description": "รหัสห้อง เช่น RM-0101"},
                    "worker_id": {"type": "string", "default": "housekeeping"},
                },
                "required": ["room_id"],
            },
        ),

        # ── Invoices ─────────────────────────────────────────
        Tool(
            name="hotel_get_invoice",
            description="ดูใบแจ้งหนี้ รายละเอียดค่าใช้จ่าย ส่วนลด VAT สำหรับการจองที่ Confirmed แล้ว",
            inputSchema={
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                },
                "required": ["reservation_id"],
            },
        ),

        # ── Reports ──────────────────────────────────────────
        Tool(
            name="hotel_report_daily_occupancy",
            description="รายงานสถานะห้องทั้งหมดวันนี้ แยกตาม Available / Hold / Occupied / Cleaning / Maintenance",
            inputSchema={"type": "object", "properties": {}},
        ),

        Tool(
            name="hotel_report_monthly_revenue",
            description="รายงานรายได้รายเดือน แยก room_income / extra_bed_income / vat / penalty",
            inputSchema={
                "type": "object",
                "properties": {
                    "year":  {"type": "integer", "description": "ปี เช่น 2025"},
                    "month": {"type": "integer", "description": "เดือน 1-12", "minimum": 1, "maximum": 12},
                },
                "required": ["year", "month"],
            },
        ),

        Tool(
            name="hotel_report_cancellations",
            description="รายงานการยกเลิกและ No-show รายไตรมาส พร้อมรวมค่าปรับที่เก็บได้",
            inputSchema={
                "type": "object",
                "properties": {
                    "year":    {"type": "integer", "description": "ปี เช่น 2025"},
                    "quarter": {"type": "integer", "description": "ไตรมาส 1-4", "minimum": 1, "maximum": 4},
                },
                "required": ["year", "quarter"],
            },
        ),

        # ── Audit Log ────────────────────────────────────────
        Tool(
            name="hotel_get_audit_log",
            description="ดู Audit Log ทั้งหมด กรองตาม action หรือ target_ref ได้",
            inputSchema={
                "type": "object",
                "properties": {
                    "action":     {"type": "string", "description": "กรอง action เช่น CANCEL_RESERVATION"},
                    "target_ref": {"type": "string", "description": "กรอง ref เช่น RSV-20250701-00001"},
                },
            },
        ),

        # ── Dev ──────────────────────────────────────────────
        Tool(
            name="hotel_seed_info",
            description="ดู seed data เริ่มต้น — รายชื่อ guest, ห้อง, กฎส่วนลดทั้งหมด (สำหรับทดสอบ)",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


# ══════════════════════════════════════════════════════════════
#  2. call_tool — Router หลัก
#     รับชื่อ tool + arguments แล้ว route ไปเรียก FastAPI
# ══════════════════════════════════════════════════════════════

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    ฟังก์ชันนี้คือ "สมอง" ของ MCP Server
    เมื่อ Claude เลือก tool ไหน จะส่งชื่อและ arguments มาที่นี่
    แล้วเราก็แปลงเป็น HTTP call ไปยัง FastAPI
    """

    result = await _dispatch(name, arguments)
    return [TextContent(type="text", text=fmt(result))]


async def _dispatch(name: str, args: dict) -> Any:
    """แยก routing ออกมาเพื่อให้อ่านง่าย"""

    # ── Auth ────────────────────────────────────────────────
    if name == "hotel_login":
        result = await call_api("POST", "/auth/login", body={
            "username": args["username"],
            "password": args["password"],
        })
        # ถ้า login สำเร็จ เก็บ token ไว้
        if not result.get("error") and "access_token" in result:
            server.context = getattr(server, "context", {})
            server.context["auth_token"] = result["access_token"]
        return result

    # ── Guests ──────────────────────────────────────────────
    if name == "hotel_register_guest":
        return await call_api("POST", "/guests", body={
            "name":        args["name"],
            "phone":       args["phone"],
            "email":       args["email"],
            "id_document": args.get("id_document", ""),
        })

    if name == "hotel_list_guests":
        return await call_api("GET", "/guests")

    if name == "hotel_get_guest":
        return await call_api("GET", f"/guests/{args['guest_id']}")

    # ── Rooms ────────────────────────────────────────────────
    if name == "hotel_list_rooms":
        params = {}
        if "room_type" in args: params["room_type"] = args["room_type"]
        if "status"    in args: params["status"]    = args["status"]
        return await call_api("GET", "/rooms", params=params)

    if name == "hotel_search_rooms":
        params = {
            "check_in":  args["check_in"],
            "check_out": args["check_out"],
        }
        if "room_type" in args: params["room_type"] = args["room_type"]
        return await call_api("GET", "/rooms/search", params=params)

    if name == "hotel_update_room_status":
        return await call_api("POST", f"/rooms/{args['room_id']}/status", body={
            "new_status": args["new_status"],
            "reason":     args.get("reason", ""),
        })

    # ── Reservations ─────────────────────────────────────────
    if name == "hotel_create_reservation":
        return await call_api("POST", "/reservations", body={
            "guest_id":       args["guest_id"],
            "room_id":        args["room_id"],
            "check_in_date":  args["check_in_date"],
            "check_out_date": args["check_out_date"],
            "channel":        args.get("channel", "Web"),
            "extra_bed":      args.get("extra_bed", False),
            "corporate_code": args.get("corporate_code", ""),
        })

    if name == "hotel_list_reservations":
        params = {}
        if "status"     in args: params["status"]     = args["status"]
        if "guest_name" in args: params["guest_name"] = args["guest_name"]
        return await call_api("GET", "/reservations", params=params)

    if name == "hotel_get_reservation":
        return await call_api("GET", f"/reservations/{args['reservation_id']}")

    if name == "hotel_confirm_reservation":
        return await call_api(
            "POST", f"/reservations/{args['reservation_id']}/confirm",
            body=_build_payment_body(args),
        )

    if name == "hotel_pay_balance":
        return await call_api(
            "POST", f"/reservations/{args['reservation_id']}/pay-balance",
            body=_build_payment_body(args),
        )

    if name == "hotel_cancel_reservation":
        return await call_api(
            "POST", f"/reservations/{args['reservation_id']}/cancel",
            body={"actor_id": args.get("actor_id", "staff_001")},
        )

    if name == "hotel_check_in":
        return await call_api(
            "POST", f"/reservations/{args['reservation_id']}/checkin",
            params={"actor_id": args.get("actor_id", "staff_001")},
        )

    if name == "hotel_check_out":
        return await call_api(
            "POST", f"/reservations/{args['reservation_id']}/checkout",
            params={"actor_id": args.get("actor_id", "staff_001")},
        )

    if name == "hotel_mark_no_show":
        return await call_api(
            "POST", f"/reservations/{args['reservation_id']}/noshow",
            params={"actor_id": args.get("actor_id", "staff_001")},
        )

    # ── Cleaning ─────────────────────────────────────────────
    if name == "hotel_complete_cleaning":
        return await call_api(
            "POST", f"/rooms/{args['room_id']}/cleaning-complete",
            params={"worker_id": args.get("worker_id", "housekeeping")},
        )

    # ── Invoices ─────────────────────────────────────────────
    if name == "hotel_get_invoice":
        return await call_api("GET", f"/invoices/{args['reservation_id']}")

    # ── Reports ──────────────────────────────────────────────
    if name == "hotel_report_daily_occupancy":
        return await call_api("GET", "/reports/daily-occupancy")

    if name == "hotel_report_monthly_revenue":
        return await call_api("GET", "/reports/monthly-revenue", params={
            "year": args["year"], "month": args["month"],
        })

    if name == "hotel_report_cancellations":
        return await call_api("GET", "/reports/cancellations", params={
            "year": args["year"], "quarter": args["quarter"],
        })

    # ── Audit Log ────────────────────────────────────────────
    if name == "hotel_get_audit_log":
        params = {}
        if "action"     in args: params["action"]     = args["action"]
        if "target_ref" in args: params["target_ref"] = args["target_ref"]
        return await call_api("GET", "/audit-log", params=params)

    # ── Dev ──────────────────────────────────────────────────
    if name == "hotel_seed_info":
        return await call_api("GET", "/dev/seed-info")

    return {"error": True, "detail": f"Unknown tool: {name}"}


def _build_payment_body(args: dict) -> dict:
    """สร้าง payment body จาก arguments — ใช้ร่วมกันระหว่าง confirm และ pay-balance"""
    return {
        "channel":         args["channel"],
        "card_number":     args.get("card_number",     "4111111111111111"),
        "card_expiry":     args.get("card_expiry",     "12/28"),
        "card_cvv":        args.get("card_cvv",        "123"),
        "bank_name":       args.get("bank_name",       "KBank"),
        "proof_url":       args.get("proof_url",       ""),
        "wallet_provider": args.get("wallet_provider", "PromptPay"),
    }


# ══════════════════════════════════════════════════════════════
#  Main — รัน MCP Server ผ่าน stdio
# ══════════════════════════════════════════════════════════════

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
