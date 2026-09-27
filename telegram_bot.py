import os
import json
import io
import urllib.parse
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from google import genai
from google.genai import types
from PIL import Image

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_TELEGRAM_USER_ID", "0"))
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)

MEMORY_FILE = "bot_memory.json"
CURRENT_MODEL = "gemini-2.0-flash"

# मेमोरी और एक्टिव एजेंट ट्रैक करने के लिए
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {"conversations": {}, "active_agent": {}}

def save_data():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# एजेंट्स की डिक्शनरी (कल हम इसे डायनामिक बनाएंगे ताकि बॉट खुद इसे अपडेट करे)
AGENTS = {
    "CEO": "You are the Master COO AI. Manage the team, give strategic advice, and coordinate tasks.",
    "HR": "You are the HR Manager. Answer strictly as an HR professional handling recruitment and team management.",
    "CREATIVE": "You are the Video & Image Director. Give creative prompts, design ideas, and visual aesthetics advice."
}

async def check_auth(update: Update) -> bool:
    user = update.effective_user
    if not user or user.id != ALLOWED_USER_ID:
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    user_id = str(update.effective_user.id)
    data["active_agent"][user_id] = "CEO"  # Default Agent
    save_data()
    
    await update.message.reply_text(
        "🏢 *Galande Ethnic HQ में आपका स्वागत है!*\n\n"
        "आपका मल्टी-एजेंट सिस्टम तैयार हो रहा है। अपना ऑफ़िस फ्लोर और एजेंट्स देखने के लिए टाइप करें:\n"
        "👉 `/office`",
        parse_mode="Markdown"
    )

async def office_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    
    # बटन्स का स्ट्रक्चर (फ्लोर प्लान)
    keyboard = [
        [InlineKeyboardButton("👑 Master COO (Main Control)", callback_data='agent_CEO')],
        [InlineKeyboardButton("👔 HR Department", callback_data='agent_HR'), 
         InlineKeyboardButton("🎨 Creative Studio", callback_data='agent_CREATIVE')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏢 **आपका वर्चुअल ऑफ़िस फ़्लोर**\n\n"
        "नीचे दिए गए बटन्स पर क्लिक करके आप अपने किसी भी डिपार्टमेंट के AI एजेंट से बात कर सकते हैं:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    choice = query.data
    
    if choice.startswith('agent_'):
        agent_name = choice.split('_')[1]
        data["active_agent"][user_id] = agent_name
        save_data()
        await query.edit_message_text(text=f"✅ **{agent_name} Agent** अब एक्टिव है!\nअब आप जो भी मैसेज भेजेंगे, उसका जवाब यही एजेंट देगा।", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return

    user_id = str(update.effective_user.id)
    user_text = update.message.text
    
    # चेक करें कि कौन सा एजेंट एक्टिव है
    active_agent = data["active_agent"].get(user_id, "CEO")
    system_instruction = AGENTS.get(active_agent, AGENTS["CEO"])

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if user_id not in data["conversations"]:
        data["conversations"][user_id] = []

    history = data["conversations"][user_id][-10:]
    history_contents = []
    for turn in history:
        history_contents.append(types.Content(role=turn["role"], parts=[types.Part.from_text(text=turn["text"])]))

    history_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))

    try:
        config = types.GenerateContentConfig(system_instruction=system_instruction)
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=history_contents,
            config=config
        )
        reply_text = response.text or "कोई प्रतिक्रिया नहीं मिली।"

        data["conversations"][user_id].append({"role": "user", "text": user_text})
        data["conversations"][user_id].append({"role": "model", "text": reply_text})
        save_data()
        
        await update.message.reply_text(f"[{active_agent}] says:\n{reply_text}")

    except Exception as e:
        await update.message.reply_text(f"त्रुटि: {str(e)}")

if __name__ == '__main__':
    print("Multi-Agent HQ Live...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("office", office_menu))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    app.run_polling()
