# app.py
import os
import threading
import asyncio
from flask import Flask, render_template, jsonify
from bot_logic import get_bot_application, bot_stats

app = Flask(__name__)

# ---------- Bot Runner (FIXED) ----------
def run_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set. Bot nahi chalega.")
        bot_stats["status"] = "No Token"
        return

    try:
        # Naya event loop banayein
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        bot_app = get_bot_application(token)
        bot_stats["status"] = "Running"
        print("✅ Bot running in background...")
        
        # close_loop=False zaroori hai warna thread loop close karne ki koshish karega
        loop.run_until_complete(
            bot_app.run_polling(drop_pending_updates=True, close_loop=False)
        )
        
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        bot_stats["status"] = "Crashed"

# ---------- Flask Routes ----------
@app.route("/")
def dashboard():
    return render_template("dashboard.html", status=bot_stats)

@app.route("/api/status")
def api_status():
    return jsonify(bot_stats)

@app.route("/health")
def health():
    return "OK", 200

# ---------- Main ----------
if __name__ == "__main__":
    # Bot ko background thread mein start karein
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 5000))
    # use_reloader=False zaroori hai taaki bot do baar start na ho
    app.run(host="0.0.0.0", port=port, use_reloader=False)
