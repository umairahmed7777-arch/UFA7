# bot.py
import os
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from telegram.constants import ChatAction
from openai import OpenAI

# Load .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN missing in .env")

# =======================
# GROQ CONFIG
# =======================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

groq = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

# =======================
# HELPERS
# =======================
def chunk_text(text: str, limit: int = 3900):
    """Split text into Telegram-safe chunks."""
    buf, size = [], 0
    for line in text.splitlines(keepends=True):
        if size + len(line) > limit:
            yield "".join(buf)
            buf, size = [line], len(line)
        else:
            buf.append(line)
            size += len(line)
    if buf:
        yield "".join(buf)

# Track if AI chat mode is ON for each chat
AI_ENABLED = {}


# =======================
# COMMANDS
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Assalamu alaikum! Bot is alive. ✅")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong 🏓")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Available Commands:
/start - Start the bot
/help - Show this help message
/ping - Check if bot is alive
/menu - To find Menu options and Buttons
/ai <query> - Ask anything from AI
/enable_ai - Enable auto AI replies
/disable_ai - Disable auto AI replies
"""
    await update.message.reply_text(help_text)


# =======================
# AI COMMAND (ON-DEMAND)/ai
# =======================
async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args).strip() if context.args else ""

    if not GROQ_API_KEY:
        await update.message.reply_text("GROQ_API_KEY missing in .env")
        return

    if not prompt:
        await update.message.reply_text("Usage:\n/ai What is 22K gold?")
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    try:
        completion = groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful, concise assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=800,
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        answer = f"⚠️ Groq error: {e}"

    for part in chunk_text(answer):
        await update.message.reply_text(part)


# =======================
# AI CHAT MODE
# =======================

async def enable_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    AI_ENABLED[chat_id] = True
    await update.message.reply_text("AI Chat Mode is ON. Send me any message ✨")


async def disable_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    AI_ENABLED[chat_id] = False
    await update.message.reply_text("AI Chat Mode is OFF. I will only respond to commands.")


async def ai_auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not AI_ENABLED.get(chat_id, False):
        return  # Do not reply

    user_text = update.message.text

    await context.bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING,
    )

    try:
        completion = groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_text},
            ],
            max_tokens=500,
            temperature=0.6,
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        answer = f"⚠️ Groq error: {e}"

    for part in chunk_text(answer):
        await update.message.reply_text(part)


# =======================
# MENU + BUTTONS
# =======================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Say Hello 👋", callback_data="hello")],
        [InlineKeyboardButton("Show Info ℹ️", callback_data="info")],
        [InlineKeyboardButton("My Creator 👨‍💻", callback_data="creator")],
    ]
    await update.message.reply_text(
        "Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "hello":
        await query.edit_message_text("Hello! 👋 How can I help you?")
    elif data == "info":
        await query.edit_message_text("This is UFA7 Bot — your personal assistant 🤖")
    elif data == "creator":
        await query.edit_message_text("This bot is created by Umair ✨")


# =======================
# MAIN
# =======================
def main():
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("enable_ai", enable_ai))
    app.add_handler(CommandHandler("disable_ai", disable_ai))

    # Buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    # Text auto-reply
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_auto_reply))

    print("Bot started. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()