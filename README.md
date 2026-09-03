# 🍜 Restaurant Agent — AI WhatsApp Ordering Bot

A WhatsApp assistant that takes restaurant orders in natural conversation. Customers message the
bot like they'd message a waiter; it reads the menu, builds the order, confirms the total, asks
pickup-or-delivery, and logs everything to a dashboard the owner can watch in real time.

The agent is **Momo**, a Nepali restaurant assistant powered by Gemini. It speaks English or
Nepali depending on how the customer writes.

---

## 🧱 Tech Stack

| Layer | Choice | Why |
|---|---|---|
| **Web framework** | Flask 3.0 | Small surface — the app is essentially one webhook plus a REST API. |
| **LLM** | Google Gemini (`gemini-2.5-flash`) via `google-genai` | Fast and cheap enough that a reply lands inside WhatsApp's timeout. |
| **Messaging** | Twilio WhatsApp API | Handles the WhatsApp Business plumbing; the app just answers a webhook with TwiML. |
| **Database** | SQLite 3 | Zero-config, file-backed. Fine for a demo; see [Limitations](#️-limitations). |
| **Frontend** | Single-file HTML + vanilla JS | No build step — `dashboard.html` polls the REST API directly. |
| **Server** | Gunicorn | Production WSGI server. Flask's dev server is for local only. |

---

## 📁 Project Structure

```
Restaurant-Agent/
├── backend/
│   ├── app.py             # Flask app: webhook, AI logic, REST API, DB layer
│   ├── test.py            # Scratch script — lists available Gemini models
│   ├── requirements.txt   # Python dependencies
│   └── .env.example       # Environment variable template
├── frontend/
│   └── dashboard.html     # Owner dashboard (served at /)
├── db/
│   └── restaurant.db      # SQLite database — auto-created, gitignored
├── setup.sh               # Creates venv + installs dependencies
└── README.md
```

---

## ⚙️ How It Works

```
Customer's WhatsApp
        │
        ▼
   Twilio  ──POST /webhook──▶  Flask
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             load history   Gemini call   save order
               (SQLite)                    (SQLite)
                                 │
        ◀──── TwiML XML reply ───┘
```

The interesting part is **order state**. Gemini is instructed to append a hidden JSON block to
every reply:

```
<ORDER_STATE>
{"items": [{"name": "chicken momo", "qty": 2, "price": 120}],
 "total": 240, "status": "ordering", "delivery_type": null, ...}
</ORDER_STATE>
```

The app strips that block before sending the message to the customer, parses it, and persists it.
So the model tracks the cart conversationally while the backend keeps a structured record — no
rigid menu-tree flow, and the dashboard still gets clean data.

The last 10 messages of history are replayed into each Gemini call, which is what lets a customer
say "make that three" and have it work.

---

## 🚀 Setup

### 1. Clone and install

```bash
git clone https://github.com/Sudin-01/Restaurant-Agent.git
cd Restaurant-Agent
./setup.sh
```

Or manually:

```bash
python3 -m venv gemini-env
source gemini-env/bin/activate
pip install -r backend/requirements.txt
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
```

Fill in `backend/.env`:

| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) — free tier is enough |
| `TWILIO_ACCOUNT_SID` | [Twilio Console](https://console.twilio.com) |
| `TWILIO_AUTH_TOKEN` | Twilio Console |
| `TWILIO_WHATSAPP_NUMBER` | Defaults to Twilio's shared sandbox — leave as-is to start |
| `PORT` | Defaults to `8080` |

### 3. Run

```bash
cd backend
python app.py
```

| Endpoint | URL |
|---|---|
| Dashboard | http://127.0.0.1:8080/ |
| Webhook | http://127.0.0.1:8080/webhook |
| Health | http://127.0.0.1:8080/health |

### 4. Expose it to Twilio

Twilio needs a public HTTPS URL to deliver messages to. For local development:

```bash
cloudflared tunnel --url http://localhost:8080
```

Copy the generated `https://….trycloudflare.com` URL into the Twilio Console under
**Messaging → Try it out → WhatsApp Sandbox**, setting *"When a message comes in"* to
`https://your-url/webhook`.

### 5. Join the sandbox

Send the join code shown in the Twilio Console (e.g. `join <two-words>`) to Twilio's sandbox
number from WhatsApp. **Every person who wants to talk to the bot has to do this once**, and
the sandbox drops them after 72 hours of inactivity.

Then just say `hi`.

---

## 📡 API Reference

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/webhook` | Twilio message webhook — returns TwiML |
| `GET` | `/api/orders` | All orders, newest first |
| `PATCH` | `/api/orders/<id>` | Update an order's status |
| `GET` | `/api/stats` | Revenue / order-count aggregates |
| `GET` | `/api/customers` | Customer list with lifetime totals |
| `GET` | `/api/conversations/<phone>` | Full message history for one number |
| `GET` | `/health` | Liveness check |

### Database Schema

**`orders`** — `id`, `phone`, `customer_name`, `items` (JSON), `total`, `status`,
`delivery_type`, `delivery_location`, `created_at`, `updated_at`

**`conversations`** — `id`, `phone`, `role`, `message`, `order_state` (JSON), `created_at`

**`customers`** — `id`, `phone` (unique), `name`, `total_orders`, `total_spent`,
`first_seen`, `last_seen`

Tables are created automatically on first run.

---

## 🍽️ Menu

Hardcoded in `app.py` as `MENU_TEXT`. The system prompt forbids inventing items or prices, so
editing that block is all it takes to change what the bot will sell.

| Item | Price (Rs.) |
|---|---|
| Chicken Momo | 120 |
| Veg Momo | 100 |
| Chowmein | 150 |
| Pizza (Medium) | 400 |
| Pizza (Large) | 700 |
| Coke | 50 |

---

## ⚠️ Limitations

This is a **demo**, and a few things are deliberately unfinished:

- **The webhook is unauthenticated.** Anyone who finds the URL can POST to it and burn your
  Gemini quota. Twilio signs its requests with `X-Twilio-Signature` — validating that is the
  first thing to add before this goes anywhere real.
- **CORS is wide open** (`Access-Control-Allow-Origin: *`), and the dashboard has no auth. Any
  visitor can read every order and conversation.
- **SQLite won't survive most hosting.** On platforms with ephemeral disks the file resets on
  every restart. Fine for a demo; swap to Postgres for anything else.
- **The dashboard polls** rather than using websockets, so it's a few seconds behind.
- **No payment handling.** Orders are confirmed, never charged.

---

## 🔐 Security Note

Never commit `backend/.env`. It's gitignored, along with `gemini-env/` and `*.db`. If a key ever
does land in a commit, revoking it is the only real fix — rewriting history doesn't help once
it's been pushed.

---

## 📄 License

MIT
