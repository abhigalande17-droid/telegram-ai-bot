import os
import json
import io
import urllib.parse
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
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

CURRENT_MODEL = "gemini-2.0-flash"

SYSTEM_INSTRUCTION = (
    "You are an elite, highly intelligent Executive AI Super-Agent. "
    "Provide razor-sharp, authentic, accurate, and deeply insightful answers. "
    "Always maintain top clarity, concrete facts, and professional precision."
)

async def check_auth(update: Update) -> bool:
    user = update.effective_user
    if not user or user.id != ALLOWED_USER_ID:
        if update.message:
            await update.message.reply_text("⛔ अनधिकृत एक्सेस: आपको इस बॉट को उपयोग करने की अनुमति नहीं है।")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    user_id = str(update.effective_user.id)
    user_conversations[user_id] = []
    save_memory(user_conversations)
    await update.message.reply_text(
        "⚡ *Executive AI Super-Agent सक्रिय है!*\n\n"
        "✨ **उपलब्ध सुपर-पावर्स:**\n"
        "• 🌐 **Google Search:** लाइव और सटीक डेटा विश्लेषण\n"
        "• 🎨 **इमेज जनरेशन:** `/image <प्रॉम्प्ट>` लिखकर HD फ़ोटो बनाएँ\n"
        "• 👁️ **विज़न विश्लेषण:** कोई भी फ़ोटो या डिज़ाइन भेजें\n"
        "• 🎙️ **वॉइस नोट्स:** बोलकर संदेश भेजें\n"
        "• 🧠 **रोलिंग मेमोरी:** निरंतर संदर्भ याद रखेगा",
        parse_mode="Markdown"
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    
    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        await update.message.reply_text("कृपया प्रॉम्प्ट दें। उदाहरण:\n`/image A royal bespoke sherwani on mannequin, studio lighting`", parse_mode="Markdown")
        return

    status_msg = await update.message.reply_text("🎨 अल्ट्रा-एचडी इमेज रेंडर हो रही है, कृपया 10-15 सेकंड प्रतीक्षा करें...")
    
    try:
        clean_prompt = prompt.replace("\n", " ").strip()
        encoded_prompt = urllib.parse.quote(clean_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed=42"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(image_url, headers=headers, timeout=60)
        
        if response.status_code == 200 and len(response.content) > 1000:
            await update.message.reply_photo(photo=io.BytesIO(response.content), caption=f"✨ `{clean_prompt}`", parse_mode="Markdown")
            await status_msg.delete()
        else:
            await update.message.reply_photo(photo=image_url, caption=f"✨ `{clean_prompt}`", parse_mode="Markdown")
            await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"इमेज जनरेशन त्रुटि: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return

    user_id = str(update.effective_user.id)
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if user_id not in user_conversations:
        user_conversations[user_id] = []

    history = user_conversations[user_id][-10:]
    history_contents = []
    for turn in history:
        history_contents.append(types.Content(role=turn["role"], parts=[types.Part.from_text(text=turn["text"])]))

    history_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))

    try:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[{"google_search": {}}]
        )
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=history_contents,
            config=config
        )
        reply_text = response.text or "कोई जवाब नहीं मिला।"

        user_conversations[user_id].append({"role": "user", "text": user_text})
        user_conversations[user_id].append({"role": "model", "text": reply_text})
        save_memory(user_conversations)

    except Exception as e:
        reply_text = f"त्रुटि: {str(e)}"

    if len(reply_text) > 4000:
        for i in range(0, len(reply_text), 4000):
            await update.message.reply_text(reply_text[i:i+4000])
    else:
        await update.message.reply_text(reply_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    caption = update.message.caption or "इस छवि का बारीक और स्पष्ट विश्लेषण करें।"

    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    image = Image.open(io.BytesIO(photo_bytes))

    try:
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=[image, caption]
        )
        await update.message.reply_text(response.text or "इमेज का विश्लेषण पूरा हुआ।")
    except Exception as e:
        await update.message.reply_text(f"विज़न त्रुटि: {str(e)}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    voice = update.message.voice or update.message.audio
    voice_file = await voice.get_file()
    audio_bytes = await voice_file.download_as_bytearray()

    try:
        audio_part = types.Part.from_bytes(data=bytes(audio_bytes), mime_type="audio/ogg")
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=[audio_part, "इस ऑडियो संदेश को सुनकर उपयुक्त और सटीक उत्तर दें।"]
        )
        await update.message.reply_text(response.text or "ऑडियो प्रोसेस हो गया।")
    except Exception as e:
        await update.message.reply_text(f"वॉइस प्रोसेसिंग त्रुटि: {str(e)}")

if __name__ == '__main__':
    print(f"Executive Super-Agent स्टार्ट हो रहा है... Active Model: {CURRENT_MODEL}")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", generate_image))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    
    app.run_polling()
