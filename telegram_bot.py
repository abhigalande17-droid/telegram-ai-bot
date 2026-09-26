import os
import json
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from google import genai
from google.genai import types

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_TELEGRAM_USER_ID", "0"))
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)

# Memory file path
MEMORY_FILE = "bot_memory.json"

# Persistent Memory Load & Save Functions
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_conversations = load_memory()

# Dynamic Model Discovery (Live Google API se model list nikalna)
def get_working_models():
    default_order = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3.8-flash"]
    try:
        models = [m.name.replace("models/", "") for m in client.models.list()]
        flash_models = [m for m in models if "flash" in m and "preview" not in m]
        return flash_models if flash_models else default_order
    except Exception:
        return default_order

ACTIVE_MODELS = get_working_models()
CURRENT_MODEL = ACTIVE_MODELS[0]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if int(user_id) != ALLOWED_USER_ID:
        await update.message.reply_text("Maaf kijiye, aapko permission nahi hai.")
        return
    
    user_conversations[user_id] = []
    save_memory(user_conversations)
    await update.message.reply_text("Namaste! Main aapka autonomous AI bot hoon. Humari saari baatcheet mujhe hamesha yaad rahegi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CURRENT_MODEL, ACTIVE_MODELS
    user_id = str(update.effective_user.id)
    
    if int(user_id) != ALLOWED_USER_ID:
        return

    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if user_id not in user_conversations:
        user_conversations[user_id] = []

    # Format history for Gemini API
    history_contents = []
    for chat in user_conversations[user_id]:
        role = "user" if chat["role"] == "user" else "model"
        history_contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=chat["text"])])
        )

    # Current user message add karein
    history_contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
    )

    reply_text = None
    models_to_try = [CURRENT_MODEL] + [m for m in ACTIVE_MODELS if m != CURRENT_MODEL]

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=history_contents,
            )
            reply_text = response.text

            # Self-healing switch update
            if model_name != CURRENT_MODEL:
                print(f"[Auto-Switch] Naya active model select hua: {model_name}")
                CURRENT_MODEL = model_name
            break
        except Exception as e:
            print(f"[Model Failed: {model_name}] Error: {e}")
            continue

    if reply_text:
        # Memory save karein
        user_conversations[user_id].append({"role": "user", "text": user_text})
        user_conversations[user_id].append({"role": "model", "text": reply_text})
        
        # Max last 14 messages preserve karein
        if len(user_conversations[user_id]) > 14:
            user_conversations[user_id] = user_conversations[user_id][-14:]
            
        save_memory(user_conversations)
    else:
        reply_text = "Sabhi AI servers par load hai, kripya 10 second baad dobara poochein."

    # Telegram message length limit handle
    if len(reply_text) > 4000:
        for i in range(0, len(reply_text), 4000):
            await update.message.reply_text(reply_text[i:i+4000])
    else:
        await update.message.reply_text(reply_text)

if __name__ == '__main__':
    print(f"Bot start ho raha hai... Default Model: {CURRENT_MODEL}")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    app.run_polling()