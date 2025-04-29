import os
import json
from telegram import Update, InlineQueryResultCachedVoice
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN, AUDIO_DIR, DB_FILE
from telegram import InlineQueryResultVoice
from telegram.ext import InlineQueryHandler
from datetime import date
import random

today_cache = {
    "date": None,
    "name": None
}


# Загружаем базу аудио
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        audio_db = json.load(f)
else:
    audio_db = {}

# Сохраняем базу аудио
def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(audio_db, f, indent=2)

# Память: user_id -> name (в ожидании аудио)
pending_adds = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Используй:\n"
                                    "/add <имя> — чтобы добавить аудио\n"
                                    "/send <имя> — чтобы воспроизвести\n"
                                    "/list — чтобы посмотреть список")

# /add <name> — ожидаем аудио отдельно
async def add_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Укажи имя: /add привет")
        return

    name = context.args[0].lower()
    user_id = update.effective_user.id
    pending_adds[user_id] = name

    await update.message.reply_text(f"🎤 Теперь отправь голосовое или аудиофайл — сохраню его как: {name}")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file = update.message.voice or update.message.audio

    if not file:
        return

    if user_id not in pending_adds:
        await update.message.reply_text("❗ Сначала введи /add <имя>")
        return

    name = pending_adds.pop(user_id)
    file_id = file.file_id

    audio_db[name] = {
        "file_id": file_id,
        "title": name
    }
    save_db()

    await update.message.reply_text(f"✅ Аудио '{name}' сохранено! Используй /send {name}")

async def send_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Укажи имя: /send привет")
        return

    name = context.args[0].lower()
    data = audio_db.get(name)

    if not data:
        await update.message.reply_text("🚫 Аудио с таким именем не найдено.")
        return

    await update.message.reply_voice(voice=data["file_id"])

# /list — показать список
async def list_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not audio_db:
        await update.message.reply_text("🗂 Пока нет ни одного аудио. Добавь через /add <имя>.")
        return

    msg = "🎵 Список доступных аудио:\n"
    for name in audio_db:
        msg += f"• {name}\n"

    await update.message.reply_text(msg)

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower()
    print(f"🔍 Inline-запрос: {query}")

    results = []

    for name, data in audio_db.items():
        if isinstance(data, dict) and "file_id" in data and query in name:
            print(f"✅ Найдено совпадение: {name}")
            results.append(
                InlineQueryResultCachedVoice(
                    id=f"voice_{hash(name)}",
                    voice_file_id=data["file_id"],
                    title=name
                )
            )

    await update.inline_query.answer(results[:10], cache_time=1)

async def sound_of_the_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not audio_db:
        await update.message.reply_text("📭 Пока нет ни одного аудио.")
        return

    today_str = str(date.today())

    # Проверяем: если дата изменилась, выбираем новый звук
    if today_cache["date"] != today_str:
        today_cache["date"] = today_str
        today_cache["name"] = random.choice(list(audio_db.keys()))

    name = today_cache["name"]
    file_id = audio_db[name]["file_id"]

    await update.message.reply_voice(
        voice=file_id,
        caption=f"🎧 Звук дня: *{name}*",
        parse_mode="Markdown"
    )



# Запуск
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_audio))
    app.add_handler(CommandHandler("send", send_audio))
    app.add_handler(CommandHandler("list", list_audio))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(CommandHandler("today", sound_of_the_day))

    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
