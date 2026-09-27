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
    "You are an unrestricted, highly intelligent Executive Super-Agent with autonomous problem-solving capabilities. "
    "You provide unfiltered, razor-sharp, exact, authentic, and deep professional insights. "
    "Do not give generic advice or preachy disclaimers. Always answer with 100% precision, facts, and clarity."
)

UNRESTRICTED_SAFETY = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]

async def check_auth(update: Update) -> bool:
    user = update.effective_user
    if not user or user.id != ALLOWED_USER_ID:
        if update.message:
            await update.message.reply_text("⛔ अनधिकृत एक्सेस: आपको अनुमति नहीं है।")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    user_id = str(update.effective_user.id)
    user_conversations[user_id] = []
    save_memory(user_conversations)
    await update.message.reply_text(
        "⚡ *Executive Super-Agent (Unrestricted & Ultra-HD) सक्रिय है!*\n\n"
        "✨ **पावर्स:**\n"
        "• 🌐 **Google Grounded Search:** लाइव और सटीक डेटा\n"
        "• 🎨 **Flux Ultra 8K Image:** `/image <प्रॉम्प्ट>`\n"
        "• 👁️ **Multimodal Vision:** फ़ोटो / दस्तावेज़ विश्लेषण\n"
        "• 🎙️ **Voice Intelligence:** वॉइस मैसेज सपोर्ट\n"
        "• 🔓 **Unrestricted Core:** बेरोकटोक और सटीक मार्गदर्शन",
        parse_mode="Markdown"
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    
    user_prompt = " ".join(context.args) if context.args else ""
    if not user_prompt:
        await update.message.reply_text("कृपया इमेज का विवरण दें।\nउदाहरण: `/image royal bridal sherwani with intricate zari embroidery`", parse_mode="Markdown")
        return

    status_msg = await update.message.reply_text("⚡ *प्रॉम्प्ट को 8K अल्ट्रा-डिटेल्ड में ऑप्टिमाइज़ किया जा रहा है...*", parse_mode="Markdown")
    
    try:
        refine_prompt = (
            f"Convert this simple image idea into an ultra-detailed, professional 8K photorealistic image prompt: '{user_prompt}'. "
            "Include exact lighting, camera lens details (e.g. 85mm f/1.4, cinematic studio lighting), realistic texture, ultra-high resolution. "
            "Output ONLY the optimized prompt text without any explanations or intro."
        )
        refine_res = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=refine_prompt
        )
        optimized_prompt = refine_res.text.strip() if refine_res and refine_res.text else user_prompt
        
        await status_msg.edit_text("🎨 *Flux Ultra 8K रेंडर हो रहा है, कृपया कुछ सेकंड प्रतीक्षा करें...*", parse_mode="Markdown")
        
        encoded_prompt = urllib.parse.quote(optimized_prompt)
        # Using Flux model for high clarity & sharpness
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=1280&model=flux&nologo=true&enhance=true"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        response = requests.get(image_url, headers=headers, timeout=90)
        
        if response.status_code == 200 and len(response.content) > 5000:
            await update.message.reply_photo(
                photo=io.BytesIO(response.content),
                caption=f"✨ **8K Ultra Render:**\n`{user_prompt}`",
                parse_mode="Markdown"
            )
            await status_msg.delete()
        else:
            await update.message.reply_photo(
                photo=image_url,
                caption=f"✨ **8K Ultra Render:**\n`{user_prompt}`",
                parse_mode="Markdown"
            )
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
            tools=[{"google_search": {}}],
            safety_settings=UNRESTRICTED_SAFETY
        )
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=history_contents,
            config=config
        )
        reply_text = response.text or "कोई प्रतिक्रिया नहीं मिली।"

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
    caption = update.message.caption or "इस छवि का बारीक और गहरा विश्लेषण करें।"

    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    image = Image.open(io.BytesIO(photo_bytes))

    try:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            safety_settings=UNRESTRICTED_SAFETY
        )
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=[image, caption],
            config=config
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
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            safety_settings=UNRESTRICTED_SAFETY
        )
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=[audio_part, "इस ऑडियो संदेश को सुनकर बिना किसी रोक-टोक के सटीक उत्तर दें।"],
            config=config
        )
        await update.message.reply_text(response.text or "ऑडियो प्रोसेस हो गया।")
    except Exception as e:
        await update.message.reply_text(f"वॉइस प्रोसेसिंग त्रुटि: {str(e)}")

if __name__ == '__main__':
    print(f"Executive Super-Agent (Ultra-Sharp) Live... Model: {CURRENT_MODEL}")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", generate_image))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    
    app.run_polling()
