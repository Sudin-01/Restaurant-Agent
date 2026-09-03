# """
# AI Restaurant Manager - WhatsApp Bot Backend
# Uses: Flask + Twilio + Claude API + SQLite
# """

# from flask import Flask, request, jsonify
# from twilio.twiml.messaging_response import MessagingResponse
# from twilio.rest import Client
# import sqlite3
# import os
# import json
# import re
# from datetime import datetime
# #import anthropic
# from google import genai
# from dotenv import load_dotenv
# from flask import make_response
# load_dotenv()

# app = Flask(__name__)

# # ─── Config ───────────────────────────────────────────────────────────────────
# #ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# client = genai.Client(api_key=GEMINI_API_KEY)
# # Keep your Twilio variables here!
# TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
# TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
# TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# # anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# # ─── Menu ─────────────────────────────────────────────────────────────────────
# MENU = {
#     "chicken momo": 120,
#     "veg momo": 100,
#     "chowmein": 150,
#     "pizza medium": 400,
#     "pizza large": 700,
#     "coke": 50,
# }

# MENU_TEXT = """
# 🍽️ *Our Menu*
# ──────────────────
# 🥟 Chicken Momo    - Rs. 120
# 🥟 Veg Momo        - Rs. 100
# 🍜 Chowmein        - Rs. 150
# 🍕 Pizza (Medium)  - Rs. 400
# 🍕 Pizza (Large)   - Rs. 700
# 🥤 Coke            - Rs. 50
# ──────────────────
# """

# SYSTEM_PROMPT = f"""You are Momo — a friendly, efficient WhatsApp restaurant assistant for a Nepali restaurant.

# {MENU_TEXT}

# 🎯 YOUR RULES:
# 1. Be SHORT (1-3 sentences max). Never write paragraphs.
# 2. Be warm, human, slightly playful but professional.
# 3. Guide every conversation toward completing an order.
# 4. NEVER invent menu items or prices not listed above.
# 5. NEVER mention being an AI.
# 6. Use simple English. If customer writes in Nepali, reply in Nepali.
# 7. Use emojis sparingly (✅ 👍 🍕 🥟).

# 📦 ORDER FLOW:
# - When customer wants to order → identify items + quantity
# - If unclear → ask ONE clarifying question
# - Calculate total → ask for confirmation
# - After confirmation → ask: pickup or delivery?
# - If delivery → ask for location
# - Then confirm: "✅ Your order is confirmed! Estimated time: 20-30 mins."

# 🛒 ORDER TRACKING:
# You will receive the current order state as JSON at the start of each message.
# Always output a JSON block at the END of your reply in this exact format (hidden from customer):
# <ORDER_STATE>
# {{
#   "items": [{{"name": "item name", "qty": 1, "price": 120}}],
#   "total": 0,
#   "status": "browsing|ordering|confirmed|delivered",
#   "delivery_type": null,
#   "delivery_location": null,
#   "customer_name": null
# }}
# </ORDER_STATE>

# 🚫 If item not on menu → say "Sorry, we don't have that. Can I suggest [relevant alternative]?"
# 💡 Upsell naturally: If someone orders momo, casually mention "Would you like a Coke to go with that? 🥤"
# """

# # ─── Database ──────────────────────────────────────────────────────────────────
# def init_db():
#     conn = sqlite3.connect("db/restaurant.db")
#     c = conn.cursor()
#     c.execute("""
#         CREATE TABLE IF NOT EXISTS orders (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             phone TEXT NOT NULL,
#             customer_name TEXT,
#             items TEXT NOT NULL,
#             total INTEGER NOT NULL,
#             status TEXT DEFAULT 'confirmed',
#             delivery_type TEXT,
#             delivery_location TEXT,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     """)
#     c.execute("""
#         CREATE TABLE IF NOT EXISTS conversations (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             phone TEXT NOT NULL,
#             role TEXT NOT NULL,
#             message TEXT NOT NULL,
#             order_state TEXT,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     """)
#     c.execute("""
#         CREATE TABLE IF NOT EXISTS customers (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             phone TEXT UNIQUE NOT NULL,
#             name TEXT,
#             total_orders INTEGER DEFAULT 0,
#             total_spent INTEGER DEFAULT 0,
#             first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     """)
#     conn.commit()
#     conn.close()

# def get_conversation_history(phone, limit=10):
#     conn = sqlite3.connect("db/restaurant.db")
#     c = conn.cursor()
#     c.execute("""
#         SELECT role, message FROM conversations 
#         WHERE phone = ? ORDER BY created_at DESC LIMIT ?
#     """, (phone, limit))
#     rows = c.fetchall()
#     conn.close()
#     # Reverse to get chronological order
#     rows.reverse()
#     return [{"role": row[0], "content": row[1]} for row in rows]

# def save_message(phone, role, message, order_state=None):
#     conn = sqlite3.connect("db/restaurant.db")
#     c = conn.cursor()
#     c.execute("""
#         INSERT INTO conversations (phone, role, message, order_state)
#         VALUES (?, ?, ?, ?)
#     """, (phone, role, message, json.dumps(order_state) if order_state else None))
#     conn.commit()
#     conn.close()

# def get_current_order_state(phone):
#     conn = sqlite3.connect("db/restaurant.db")
#     c = conn.cursor()
#     c.execute("""
#         SELECT order_state FROM conversations 
#         WHERE phone = ? AND order_state IS NOT NULL
#         ORDER BY created_at DESC LIMIT 1
#     """, (phone,))
#     row = c.fetchone()
#     conn.close()
#     if row and row[0]:
#         return json.loads(row[0])
#     return {"items": [], "total": 0, "status": "browsing", "delivery_type": None, "delivery_location": None, "customer_name": None}

# def save_order(phone, order_state):
#     if order_state.get("status") == "confirmed" and order_state.get("items"):
#         conn = sqlite3.connect("db/restaurant.db")
#         c = conn.cursor()
#         # Check if order already saved for this session
#         c.execute("""
#             SELECT id FROM orders WHERE phone = ? 
#             AND created_at > datetime('now', '-1 hour')
#             AND status = 'confirmed'
#             ORDER BY created_at DESC LIMIT 1
#         """, (phone,))
#         existing = c.fetchone()
        
#         if not existing:
#             c.execute("""
#                 INSERT INTO orders (phone, customer_name, items, total, status, delivery_type, delivery_location)
#                 VALUES (?, ?, ?, ?, ?, ?, ?)
#             """, (
#                 phone,
#                 order_state.get("customer_name"),
#                 json.dumps(order_state.get("items", [])),
#                 order_state.get("total", 0),
#                 "confirmed",
#                 order_state.get("delivery_type"),
#                 order_state.get("delivery_location")
#             ))
#             # Update customer stats
#             c.execute("""
#                 INSERT INTO customers (phone, total_orders, total_spent, last_seen)
#                 VALUES (?, 1, ?, CURRENT_TIMESTAMP)
#                 ON CONFLICT(phone) DO UPDATE SET
#                     total_orders = total_orders + 1,
#                     total_spent = total_spent + ?,
#                     last_seen = CURRENT_TIMESTAMP
#             """, (phone, order_state.get("total", 0), order_state.get("total", 0)))
        
#         conn.commit()
#         conn.close()

# def extract_order_state(text):
#     """Extract JSON order state from AI response"""
#     match = re.search(r'<ORDER_STATE>(.*?)</ORDER_STATE>', text, re.DOTALL)
#     if match:
#         try:
#             return json.loads(match.group(1).strip())
#         except:
#             return None
#     return None

# def clean_response(text):
#     """Remove the ORDER_STATE block from customer-facing response"""
#     return re.sub(r'<ORDER_STATE>.*?</ORDER_STATE>', '', text, flags=re.DOTALL).strip()

# # ─── AI Response ──────────────────────────────────────────────────────────────
# # def get_ai_response(phone, user_message):
# #     history = get_conversation_history(phone, limit=12)
# #     order_state = get_current_order_state(phone)
    
# #     # Inject current order state into user message for context
# #     context_message = f"[Current order state: {json.dumps(order_state)}]\n\nCustomer: {user_message}"
    
# #     messages = history + [{"role": "user", "content": context_message}]
    
# #     response = anthropic_client.messages.create(
# #         model="claude-sonnet-4-20250514",
# #         max_tokens=500,
# #         system=SYSTEM_PROMPT,
# #         messages=messages
# #     )
    
# #     full_response = response.content[0].text
# #     new_order_state = extract_order_state(full_response)
# #     clean_text = clean_response(full_response)
    
# #     # Save to DB
# #     save_message(phone, "user", user_message, order_state)
# #     save_message(phone, "assistant", clean_text, new_order_state or order_state)
    
# #     # Save order if confirmed
# #     if new_order_state and new_order_state.get("status") == "confirmed":
# #         save_order(phone, new_order_state)
    
# #     return clean_text
# def get_ai_response(phone, user_message):
#     history = get_conversation_history(phone, limit=12)
#     order_state = get_current_order_state(phone)
    
#     context_message = f"[Current order state: {json.dumps(order_state)}]\n\nCustomer: {user_message}"
    
#     # Format history for the new SDK
#     gemini_history = []
#     for msg in history:
#         role = "model" if msg["role"] == "assistant" else "user"
#         gemini_history.append({"role": role, "parts": [{"text": msg["content"]}]})
    
#     # Use the new models.generate_content_stream or generate_content
#     response = client.models.generate_content(
#         model="gemini-2.5-flash",
#         config={
#             "system_instruction": SYSTEM_PROMPT,
#         },
#         contents=gemini_history + [{"role": "user", "parts": [{"text": context_message}]}]
#     )
    
#     full_response = response.text
#     new_order_state = extract_order_state(full_response)
#     clean_text = clean_response(full_response)
    
#     save_message(phone, "user", user_message, order_state)
#     save_message(phone, "assistant", clean_text, new_order_state or order_state)
    
#     if new_order_state and new_order_state.get("status") == "confirmed":
#         save_order(phone, new_order_state)
    
#     return clean_text
# # ─── Routes ───────────────────────────────────────────────────────────────────
# # @app.route("/webhook", methods=["POST"])
# # def webhook():
# #     """Twilio WhatsApp webhook"""
# #     incoming_msg = request.values.get("Body", "").strip()
# #     from_number = request.values.get("From", "")
    
# #     if not incoming_msg:
# #         return str(MessagingResponse())
    
# #     try:
# #         ai_reply = get_ai_response(from_number, incoming_msg)
# #     except Exception as e:
# #         print(f"Error: {e}")
# #         ai_reply = "Sorry, I'm having a little trouble right now. Please try again in a moment! 🙏"
    
# #     resp = MessagingResponse()
# #     resp.message(ai_reply)
# #     return str(resp)
# @app.route("/webhook", methods=["POST"])
# def webhook():
#     """Twilio WhatsApp webhook"""
#     incoming_msg = request.values.get("Body", "").strip()
#     from_number = request.values.get("From", "")
    
#     if not incoming_msg:
#         return str(MessagingResponse())
    
#     try:
#         ai_reply = get_ai_response(from_number, incoming_msg)
#     except Exception as e:
#         print(f"Error: {e}")
#         ai_reply = "Sorry, I'm having a little trouble right now. Please try again in a moment! 🙏"
    
#     # 1. Create the Twilio Response
#     resp = MessagingResponse()
#     resp.message(ai_reply)
    
#     # 2. Wrap it in a Flask response object
#     response = make_response(str(resp))
    
#     # 3. ADD THIS LINE: It bypasses the 403/warning page for ngrok free accounts
#     response.headers['ngrok-skip-browser-warning'] = 'true'
    
#     return response

# # ─── Dashboard API ────────────────────────────────────────────────────────────
# @app.route("/api/orders", methods=["GET"])
# def get_orders():
#     conn = sqlite3.connect("db/restaurant.db")
#     conn.row_factory = sqlite3.Row
#     c = conn.cursor()
#     status_filter = request.args.get("status", "")
#     if status_filter:
#         c.execute("SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT 50", (status_filter,))
#     else:
#         c.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50")
#     orders = [dict(row) for row in c.fetchall()]
#     for o in orders:
#         o["items"] = json.loads(o["items"])
#     conn.close()
#     return jsonify(orders)

# @app.route("/api/orders/<int:order_id>", methods=["PATCH"])
# def update_order(order_id):
#     data = request.json
#     new_status = data.get("status")
#     conn = sqlite3.connect("db/restaurant.db")
#     c = conn.cursor()
#     c.execute("UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, order_id))
#     conn.commit()
#     conn.close()
#     return jsonify({"success": True})

# @app.route("/api/stats", methods=["GET"])
# def get_stats():
#     conn = sqlite3.connect("db/restaurant.db")
#     c = conn.cursor()
    
#     c.execute("SELECT COUNT(*) FROM orders")
#     total_orders = c.fetchone()[0]
    
#     c.execute("SELECT SUM(total) FROM orders")
#     total_revenue = c.fetchone()[0] or 0
    
#     c.execute("SELECT COUNT(*) FROM orders WHERE status = 'confirmed'")
#     pending = c.fetchone()[0]
    
#     c.execute("SELECT COUNT(DISTINCT phone) FROM customers")
#     total_customers = c.fetchone()[0]
    
#     c.execute("""
#         SELECT COUNT(*) FROM orders 
#         WHERE created_at > datetime('now', '-1 day')
#     """)
#     today_orders = c.fetchone()[0]

#     c.execute("""
#         SELECT SUM(total) FROM orders 
#         WHERE created_at > datetime('now', '-1 day')
#     """)
#     today_revenue = c.fetchone()[0] or 0
    
#     # Popular items
#     c.execute("SELECT items FROM orders")
#     all_items = c.fetchall()
#     item_counts = {}
#     for row in all_items:
#         items = json.loads(row[0])
#         for item in items:
#             name = item.get("name", "")
#             qty = item.get("qty", 1)
#             item_counts[name] = item_counts.get(name, 0) + qty
    
#     popular = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
#     conn.close()
#     return jsonify({
#         "total_orders": total_orders,
#         "total_revenue": total_revenue,
#         "pending_orders": pending,
#         "total_customers": total_customers,
#         "today_orders": today_orders,
#         "today_revenue": today_revenue,
#         "popular_items": [{"name": k, "count": v} for k, v in popular]
#     })

# @app.route("/api/customers", methods=["GET"])
# def get_customers():
#     conn = sqlite3.connect("db/restaurant.db")
#     conn.row_factory = sqlite3.Row
#     c = conn.cursor()
#     c.execute("SELECT * FROM customers ORDER BY total_orders DESC LIMIT 30")
#     customers = [dict(row) for row in c.fetchall()]
#     conn.close()
#     return jsonify(customers)

# @app.route("/api/conversations/<phone>", methods=["GET"])
# def get_conversation(phone):
#     phone = phone.replace("-", "+")
#     conn = sqlite3.connect("db/restaurant.db")
#     conn.row_factory = sqlite3.Row
#     c = conn.cursor()
#     c.execute("""
#         SELECT role, message, created_at FROM conversations 
#         WHERE phone = ? ORDER BY created_at ASC LIMIT 50
#     """, (phone,))
#     msgs = [dict(row) for row in c.fetchall()]
#     conn.close()
#     return jsonify(msgs)

# @app.route("/health")
# def health():
#     return jsonify({"status": "ok", "time": datetime.now().isoformat()})

# # ─── Init ──────────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     os.makedirs("db", exist_ok=True)
#     init_db()
#     print("🍽️  AI Restaurant Manager running on http://0.0.0.0:5000")
#     # Change 'debug=True' to include 'host' and 'port' explicitly
#     app.run(host='0.0.0.0', port=5000, debug=True)





"""
AI Restaurant Manager - WhatsApp Bot Backend
Uses: Flask + Twilio + Gemini API + SQLite
"""

from flask import Flask, request, jsonify, send_from_directory, make_response
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import os
import json
import re
from datetime import datetime
from google import genai
from dotenv import load_dotenv

load_dotenv()

# ─── App Setup ────────────────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')

# ─── CORS ─────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, OPTIONS'
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

@app.route('/api/<path:path>', methods=['OPTIONS'])
def options_handler(path=''):
    return make_response('', 204)

# ─── Config ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

TWILIO_ACCOUNT_SID     = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN      = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# ─── Menu ─────────────────────────────────────────────────────────────────────
MENU_TEXT = """
🍽️ *Our Menu*
──────────────────
🥟 Chicken Momo    - Rs. 120
🥟 Veg Momo        - Rs. 100
🍜 Chowmein        - Rs. 150
🍕 Pizza (Medium)  - Rs. 400
🍕 Pizza (Large)   - Rs. 700
🥤 Coke            - Rs. 50
──────────────────
"""

SYSTEM_PROMPT = f"""You are Momo — a friendly, efficient WhatsApp restaurant assistant for a Nepali restaurant.

{MENU_TEXT}

🎯 YOUR RULES:
1. Be SHORT (1-3 sentences max). Never write paragraphs.
2. Be warm, human, slightly playful but professional.
3. Guide every conversation toward completing an order.
4. NEVER invent menu items or prices not listed above.
5. NEVER mention being an AI.
6. Use simple English. If customer writes in Nepali, reply in Nepali.
7. Use emojis sparingly (✅ 👍 🍕 🥟).

📦 ORDER FLOW:
- When customer wants to order → identify items + quantity
- If unclear → ask ONE clarifying question
- Calculate total → ask for confirmation
- After confirmation → ask: pickup or delivery?
- If delivery → ask for location
- Then confirm: "✅ Your order is confirmed! Estimated time: 20-30 mins."

🛒 ORDER TRACKING:
You will receive the current order state as JSON at the start of each message.
Always output a JSON block at the END of your reply in this exact format (hidden from customer):
<ORDER_STATE>
{{
  "items": [{{"name": "item name", "qty": 1, "price": 120}}],
  "total": 0,
  "status": "browsing|ordering|confirmed|delivered",
  "delivery_type": null,
  "delivery_location": null,
  "customer_name": null
}}
</ORDER_STATE>

🚫 If item not on menu → say "Sorry, we don't have that. Can I suggest [relevant alternative]?"
💡 Upsell naturally: If someone orders momo, casually mention "Would you like a Coke to go with that? 🥤"
"""

# ─── Database ─────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db', 'restaurant.db')

def get_conn():
    # timeout: wait up to 10s for a lock instead of raising "database is locked".
    # WAL lets reads and a write proceed concurrently across threads.
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            customer_name TEXT,
            items TEXT NOT NULL,
            total INTEGER NOT NULL,
            status TEXT DEFAULT 'confirmed',
            delivery_type TEXT,
            delivery_location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            order_state TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            name TEXT,
            total_orders INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_conversation_history(phone, limit=10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT role, message FROM conversations
        WHERE phone = ? ORDER BY created_at DESC LIMIT ?
    """, (phone, limit))
    rows = c.fetchall()
    conn.close()
    rows.reverse()
    return [{"role": row[0], "content": row[1]} for row in rows]

def save_message(phone, role, message, order_state=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO conversations (phone, role, message, order_state)
        VALUES (?, ?, ?, ?)
    """, (phone, role, message, json.dumps(order_state) if order_state else None))
    conn.commit()
    conn.close()

def get_current_order_state(phone):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT order_state FROM conversations
        WHERE phone = ? AND order_state IS NOT NULL
        ORDER BY created_at DESC LIMIT 1
    """, (phone,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return {"items": [], "total": 0, "status": "browsing",
            "delivery_type": None, "delivery_location": None, "customer_name": None}

def save_order(phone, order_state):
    if not (order_state.get("status") == "confirmed" and order_state.get("items")):
        return
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id FROM orders WHERE phone = ?
        AND created_at > datetime('now', '-1 hour')
        AND status = 'confirmed'
        ORDER BY created_at DESC LIMIT 1
    """, (phone,))
    if not c.fetchone():
        c.execute("""
            INSERT INTO orders (phone, customer_name, items, total, status, delivery_type, delivery_location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            phone,
            order_state.get("customer_name"),
            json.dumps(order_state.get("items", [])),
            order_state.get("total", 0),
            "confirmed",
            order_state.get("delivery_type"),
            order_state.get("delivery_location"),
        ))
        c.execute("""
            INSERT INTO customers (phone, total_orders, total_spent, last_seen)
            VALUES (?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(phone) DO UPDATE SET
                total_orders = total_orders + 1,
                total_spent  = total_spent  + ?,
                last_seen    = CURRENT_TIMESTAMP
        """, (phone, order_state.get("total", 0), order_state.get("total", 0)))
    conn.commit()
    conn.close()

def extract_order_state(text):
    match = re.search(r'<ORDER_STATE>(.*?)</ORDER_STATE>', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            return None
    return None

def clean_response(text):
    return re.sub(r'<ORDER_STATE>.*?</ORDER_STATE>', '', text, flags=re.DOTALL).strip()

# ─── AI Response (Gemini) ─────────────────────────────────────────────────────
def get_ai_response(phone, user_message):
    history     = get_conversation_history(phone, limit=12)
    order_state = get_current_order_state(phone)

    context_message = f"[Current order state: {json.dumps(order_state)}]\n\nCustomer: {user_message}"

    gemini_history = []
    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_history.append({"role": role, "parts": [{"text": msg["content"]}]})

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config={"system_instruction": SYSTEM_PROMPT},
        contents=gemini_history + [{"role": "user", "parts": [{"text": context_message}]}],
    )

    full_response   = response.text
    new_order_state = extract_order_state(full_response)
    clean_text      = clean_response(full_response)

    save_message(phone, "user",      user_message, order_state)
    save_message(phone, "assistant", clean_text,   new_order_state or order_state)

    if new_order_state and new_order_state.get("status") == "confirmed":
        save_order(phone, new_order_state)

    return clean_text

# ─── Dashboard ────────────────────────────────────────────────────────────────
@app.route('/')
def dashboard():
    return send_from_directory(FRONTEND_DIR, 'dashboard.html')

# ─── Webhook ──────────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    from_number  = request.values.get("From", "")

    if not incoming_msg:
        return str(MessagingResponse())

    try:
        ai_reply = get_ai_response(from_number, incoming_msg)
    except Exception as e:
        import traceback
        print(f"[ERROR] webhook failed: {e}")
        traceback.print_exc()
        ai_reply = "Sorry, I'm having a little trouble right now. Please try again! 🙏"

    resp = MessagingResponse()
    resp.message(ai_reply)
    response = make_response(str(resp))
    response.headers['Content-Type'] = 'text/xml'
    return response

# ─── API ──────────────────────────────────────────────────────────────────────
@app.route("/api/orders", methods=["GET"])
def get_orders():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    status_filter = request.args.get("status", "")
    if status_filter:
        c.execute("SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT 50", (status_filter,))
    else:
        c.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50")
    orders = [dict(row) for row in c.fetchall()]
    conn.close()
    for o in orders:
        o["items"] = json.loads(o["items"])
    return jsonify(orders)

@app.route("/api/orders/<int:order_id>", methods=["PATCH"])
def update_order(order_id):
    data       = request.json
    new_status = data.get("status")
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
              (new_status, order_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/stats", methods=["GET"])
def get_stats():
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(total), 0) FROM orders")
    total_revenue = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'confirmed'")
    pending = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT phone) FROM customers")
    total_customers = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE created_at > datetime('now', '-1 day')")
    today_orders = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(total), 0) FROM orders WHERE created_at > datetime('now', '-1 day')")
    today_revenue = c.fetchone()[0]

    c.execute("SELECT items FROM orders")
    item_counts = {}
    for (raw,) in c.fetchall():
        for item in json.loads(raw):
            name = item.get("name", "")
            item_counts[name] = item_counts.get(name, 0) + item.get("qty", 1)
    popular = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    conn.close()
    return jsonify({
        "total_orders":    total_orders,
        "total_revenue":   total_revenue,
        "pending_orders":  pending,
        "total_customers": total_customers,
        "today_orders":    today_orders,
        "today_revenue":   today_revenue,
        "popular_items":   [{"name": k, "count": v} for k, v in popular],
    })

@app.route("/api/customers", methods=["GET"])
def get_customers():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM customers ORDER BY total_orders DESC LIMIT 30")
    customers = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(customers)

@app.route("/api/conversations/<path:phone>", methods=["GET"])
def get_conversation(phone):
    phone = phone.replace("-", "+")
    if not phone.startswith("whatsapp:"):
        phone = "whatsapp:" + phone
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT role, message, created_at FROM conversations
        WHERE phone = ? ORDER BY created_at ASC LIMIT 50
    """, (phone,))
    msgs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(msgs)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

# ─── Start ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    PORT = int(os.getenv("PORT", 8080))
    print(f"\n🍽️  AI Restaurant Manager")
    print(f"   Dashboard  →  http://127.0.0.1:{PORT}/")
    print(f"   Webhook    →  http://127.0.0.1:{PORT}/webhook")
    print(f"   Health     →  http://127.0.0.1:{PORT}/health\n")
    app.run(host='0.0.0.0', port=PORT, debug=True)
