# lang: Python | file: main.py | target: Render (Linux) | Telegram Bot API

import os
import requests
import random
import threading
import time
import asyncio
from aiohttp import web
import telebot

# ==========================================
# TOKENLAR
# ==========================================
DEFAULT_TOKENS = [
    "8612500307:AAHZ1prbGS9ii5J7rA4PiLKSuztfBSYurlQ",
    "9164860532:AAEOiVLJe6Ogh7KBaVNeqHeSplj2zqg9YpY",
    "8850107704:AAFBcn3n3cJW7DUPg5dwvyhMVdw-0j_KraU",
    "9016231632:AAHv58jUef2Zo0qXJcfP6qyXsh5_smbbMYk",
    "9002507003:AAG5fOIyqcOGEi5agEEHk9uqNzIS__zpiQI",
    "9261820651:AAGjVBWAKpOthpSE8H4yn4OuSDYhdKJNzrc",
    "9161857693:AAH0FKe_64a0hlBAOEl1XSV3RKio9HcAB2U",
    "9168857205:AAE_y2wmhnRoDc1cdoilYeWsTx1paJXYOOU",
    "9020615009:AAEbV8864UbsaI5S7z09mmaxN9s9yUS71TE",
    "8846195735:AAG31765-y8ZSpfWGB38xPFkwxwNKih0Wvc",
    "8684961175:AAF-EugA4UUMEnOKuNRGxHAg7L5UK-hA9xw",
    "8614193525:AAHmPEuVyLGf9y_1Pk32Bi_7wOthGdoVTF0",
    "8892329293:AAE81rvRwv37Duklrgq80tdo9xULDTZM-3A",
    "8839585037:AAHiLdafW4gdJllq6XYcWVHEiMNOxvXIIDw",
    "8780781642:AAFKuXw5lgJrmJotxdslvV6Y-_F7TKYPrkg",
    "8230491436:AAErxaPtJKHZWi70QCu4jc4P-PY9ZHsUnqU",
    "8730555029:AAHuY0QSrgJ1OX6NSFriiP9otWK_0dyy1zc",
    "8480258106:AAGaYgSgPdHFeO_ZGIZBAQKNV55fMFEYwWc",
    "8796590031:AAHTHpEOkWLfJHVHCd6MpZHy0q6rHOCSYls",
    "9297134834:AAGkctplyIbFFOI0hD7npFkGmNM3nokznpA",
]

REACTIONS = [
    "😎", "🥳", "🤩", "😱", "😰", "🤯", "😳", "🤔", "😁", "👍",
    "✊", "🐳", "🕊", "⛄️", "❤️", "🤝", "🫂", "👌", "👏", "😇",
    "🥶", "🙏", "🔥", "🏆", "❤️‍🔥", "💔", "💖", "💪", "🙀",
    "🎉", "🎄", "🎊"
]

RESTART_DELAY = 3
MAX_RESTARTS  = 500

seen_lock     = threading.Lock()
seen_messages = set()


# ==========================================
# REAKSIYA YUBORUVCHI
# ==========================================
def send_reaction(token, chat_id, message_id, index):
    bot_id  = token.split(":")[0]
    emoji   = random.choice(REACTIONS)
    url     = f"https://api.telegram.org/bot{token}/setMessageReaction"
    payload = {
        "chat_id"    : chat_id,
        "message_id" : message_id,
        "reaction"   : [{"type": "emoji", "emoji": emoji}],
        "is_big"     : False,
    }

    time.sleep(index * 0.15)  # staggered — parallel conflict oldini oladi

    for attempt in range(5):
        try:
            resp = requests.post(url, json=payload, timeout=10)

            if resp.status_code == 200:
                print(f"[{bot_id}] ✅ {emoji}")
                return

            elif resp.status_code == 429:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 3)
                print(f"[{bot_id}] ⏳ rate limit — {retry_after}s")
                time.sleep(retry_after + 0.5)

            elif resp.status_code in (400, 403):
                err = resp.json().get("description", "")
                print(f"[{bot_id}] ⚠️ {resp.status_code}: {err}")
                return

            else:
                print(f"[{bot_id}] ❌ {resp.status_code}")
                time.sleep(1)

        except requests.exceptions.Timeout:
            print(f"[{bot_id}] ⏱ timeout #{attempt + 1}")
            time.sleep(2)
        except Exception as e:
            print(f"[{bot_id}] 💥 {e}")
            time.sleep(1)

    print(f"[{bot_id}] 🔴 5 urinish bajarilmadi")


def trigger_all(chat_id, message_id, tokens):
    for idx, token in enumerate(tokens):
        threading.Thread(
            target=send_reaction,
            args=(token, chat_id, message_id, idx),
            daemon=True,
        ).start()


# ==========================================
# WEBHOOK TOZALASH
# ==========================================
def delete_webhook(token):
    try:
        requests.get(
            f"https://api.telegram.org/bot{token}/deleteWebhook"
            "?drop_pending_updates=True",
            timeout=5,
        )
    except Exception:
        pass


# ==========================================
# ASOSIY LISTENER
# ==========================================
def run_main_listener(token, all_tokens):
    bot_id   = token.split(":")[0]
    restarts = 0

    while restarts < MAX_RESTARTS:
        delete_webhook(token)
        bot = telebot.TeleBot(token, num_threads=4)

        @bot.message_handler(commands=["start"])
        def on_start(msg):
            try:
                bot.send_message(msg.chat.id, f"✅ Listener ({bot_id}) faol!")
            except Exception:
                pass

        @bot.channel_post_handler(content_types=[
            "text", "photo", "video", "audio", "document",
            "voice", "video_note", "sticker", "animation",
            "poll", "location", "contact", "venue"
        ])
        def on_post(msg):
            key = (msg.chat.id, msg.message_id)
            with seen_lock:
                seen_messages.add(key)
                if len(seen_messages) > 1000:
                    seen_messages.clear()
            print(f"[MAIN:{bot_id}] 📨 chat:{msg.chat.id} msg:{msg.message_id}")
            trigger_all(msg.chat.id, msg.message_id, all_tokens)

        @bot.edited_channel_post_handler(content_types=[
            "text", "photo", "video", "document"
        ])
        def on_edit(msg):
            key = (msg.chat.id, msg.message_id)
            with seen_lock:
                seen_messages.add(key)
            trigger_all(msg.chat.id, msg.message_id, all_tokens)

        try:
            print(f"[MAIN:{bot_id}] 🟢 Polling #{restarts + 1}")
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=20,
                interval=0,
                allowed_updates=["channel_post", "edited_channel_post", "message"],
            )
        except Exception as e:
            print(f"[MAIN:{bot_id}] 💥 {e}")
        finally:
            try:
                bot.stop_polling()
            except Exception:
                pass

        restarts += 1
        print(f"[MAIN:{bot_id}] 🔄 {RESTART_DELAY}s dan so'ng qayta...")
        time.sleep(RESTART_DELAY)

    print(f"[MAIN:{bot_id}] 🔴 Max restart.")


# ==========================================
# BACKUP LISTENERLAR
# ==========================================
def run_backup_listener(token, all_tokens, backup_index):
    bot_id   = token.split(":")[0]
    restarts = 0

    time.sleep(2 + backup_index * 1)  # asosiydan keyin ishga tushadi

    while restarts < MAX_RESTARTS:
        delete_webhook(token)
        bot = telebot.TeleBot(token, num_threads=2)

        @bot.channel_post_handler(content_types=[
            "text", "photo", "video", "audio", "document",
            "voice", "video_note", "sticker", "animation",
            "poll", "location", "contact", "venue"
        ])
        def on_post(msg):
            key = (msg.chat.id, msg.message_id)
            with seen_lock:
                if key in seen_messages:
                    return
                seen_messages.add(key)
                if len(seen_messages) > 1000:
                    seen_messages.clear()
            print(f"[BACKUP:{bot_id}] 📨 ushlanmagan post — trigger!")
            trigger_all(msg.chat.id, msg.message_id, all_tokens)

        @bot.edited_channel_post_handler(content_types=[
            "text", "photo", "video", "document"
        ])
        def on_edit(msg):
            key = (msg.chat.id, msg.message_id)
            with seen_lock:
                if key in seen_messages:
                    return
                seen_messages.add(key)
            trigger_all(msg.chat.id, msg.message_id, all_tokens)

        try:
            print(f"[BACKUP:{bot_id}] 🟡 Polling #{restarts + 1}")
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=20,
                interval=0,
                allowed_updates=["channel_post", "edited_channel_post"],
            )
        except Exception as e:
            print(f"[BACKUP:{bot_id}] 💥 {e}")
        finally:
            try:
                bot.stop_polling()
            except Exception:
                pass

        restarts += 1
        time.sleep(RESTART_DELAY)


# ==========================================
# WEB SERVER — UptimeRobot ping uchun
# ==========================================
async def handle_ping(request):
    return web.Response(text="✅ Reaction bots alive!")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    port    = int(os.getenv("PORT", 10000))
    runner  = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server :{port} da ishga tushdi")

def run_web():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_web())
    loop.run_forever()


# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    env = os.getenv("BOT_TOKEN")
    if env:
        tokens = list(dict.fromkeys(t.strip() for t in env.split(",") if t.strip()))
    else:
        tokens = list(dict.fromkeys(DEFAULT_TOKENS))

    print(f"📋 Jami {len(tokens)} ta token yuklandi")

    # 1 — web server
    threading.Thread(target=run_web, daemon=True).start()
    time.sleep(0.5)

    # 2 — asosiy listener (tokens[0])
    threading.Thread(
        target=run_main_listener,
        args=(tokens[0], tokens),
        daemon=True,
    ).start()

    # 3 — backup listenerlar (tokens[1], tokens[2])
    backup_count = min(2, len(tokens) - 1)
    for i in range(1, 1 + backup_count):
        threading.Thread(
            target=run_backup_listener,
            args=(tokens[i], tokens, i),
            daemon=True,
        ).start()

    print(f"🚀 1 asosiy + {backup_count} backup listener ishga tushdi")
    print(f"🎯 Reaksiya bosuvchilar: barcha {len(tokens)} ta token")

    while True:
        time.sleep(60)