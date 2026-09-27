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

MASTER_SYSTEM_INSTRUCTION = (
    "You are the ultimate autonomous Executive Super-Agent and Private Strategic Advisor. "
    "You operate with elite intelligence, extreme sharpness, authentic depth, and uncompromising accuracy. "
    "Guidelines:\n"
    "1. Never give generic, robotic, or preachy disclaimers. Speak directly, professionally, and decisively.\n"
    "2. Provide razor-sharp logical analysis, strategic insights, concrete data points, and actionable execution plans.\n"
    "3. Maintain seamless continuity across all previous interactions. Remember user intent, context, and preferences.\n"
    "4. When analyzing business, design, technical, or financial topics, deliver top-tier expert consultation.\n"
    "5. Adapt naturally to the user's preferred language (Hindi, Hinglish, Marathi, English) with natural elegance and confidence."
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
        "⚡ *Autonomous Executive Super-Agent v2.0 सक्रिय है!*\n\n"
        "🧠 **इंटीग्रेटेड सुपर-पावर्स:**\n"
        "• ⚡ **Deep Memory & Context:** पिछली सभी बातें याद रखेगा\n"
        "• 🌐 **Live Google Grounding:** लाइव डेटा और रिसर्च\n"
        "• 🎨 **Flux/Turbo 8K Engine:** `/image <विवरण>`\n"
        "• 👁️ **Multi-Modal Vision:** किसी भी फ़ोटो/दस्तावेज़ का विश्लेषण\n"
        "• 🎙️ **Voice Processing:** वॉयस नोट्स को समझकर त्वरित समाधान\n"
        "• 🔓 **Unrestricted Executive Core:** बिना किसी रुकावट के ठोस उत्तर\n\n"
        "आप किसी भी प्रोजेक्ट, स्ट्रेटेजी, डिज़ाइन या टास्क पर सीधा संवाद शुरू कर सकते हैं।",
        parse_mode="Markdown"
    )

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    user_id = str(update.effective_user.id)
    user_conversations[user_id] = []
    save_memory(user_conversations)
    await update.message.reply_text("🧹 *मेमोरी साफ़ कर दी गई है। एक नई बातचीत शुरू की जा सकती है।*", parse_mode="Markdown")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    
    user_prompt = " ".join(context.args) if context.args else ""
    if not user_prompt:
        await update.message.reply_text("कृपया इमेज का विवरण दें।\nउदाहरण: `/image royal designer ghagra suit on mannequin in luxury boutique 8k resolution`", parse_mode="Markdown")
        return

    status_msg = await update.message.reply_text("🎨 *अल्ट्रा-एचडी 8K इमेज रेंडर हो रही है, कृपया 10-15 सेकंड प्रतीक्षा करें...*", parse_mode="Markdown")
    
    try:
        # Prompt Auto-Enhance for Ultra Clarity
        refine_prompt = (
            f"Transform this into an ultra-detailed, 8K professional photography prompt: '{user_prompt}'. "
            "Focus on photorealism, exquisite textures, cinematic studio lighting, highly intricate details, 85mm lens. "
            "Output ONLY the prompt text, no intro."
        )
        try:
            refine_res = client.models.generate_content(
                model=CURRENT_MODEL,
                contents=refine_prompt
            )
            final_prompt = refine_res.text.strip() if refine_res and refine_res.text else user_prompt
        except Exception:
            final_prompt = f"{user_prompt}, highly detailed, sharp focus, 8k resolution, professional photography, realistic fabric textures"

        clean_prompt = final_prompt.replace("\n", " ").strip()
        encoded_prompt = urllib.parse.quote(clean_prompt)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        # Try Flux model first
        flux_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&seed=101"
        response = requests.get(flux_url, headers=headers, timeout=50)

        # Fallback to turbo if flux takes too long
        if response.status_code != 200 or len(response.content) < 5000:
            turbo_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=turbo&nologo=true"
            response = requests.get(turbo_url, headers=headers, timeout=35)

        if response.status_code == 200 and len(response.content) > 5000:
            image_stream = io.BytesIO(response.content)
            image_stream.name = "render_8k.jpg"
            await update.message.reply_photo(
                photo=image_stream,
                caption=f"✨ *8K Ultra Render:*\n`{user_prompt}`",
                parse_mode="Markdown"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("इमेज रेंडर नहीं हो सकी। कृपया थोड़ी देर बाद पुनः प्रयास करें।")
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

    # Deep Rolling Context (Keeps last 30 conversation turns)
    history = user_conversations[user_id][-30:]
    history_contents = []
    for turn in history:
        history_contents.append(types.Content(role=turn["role"], parts=[types.Part.from_text(text=turn["text"])]))

    history_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))

    try:
        config = types.GenerateContentConfig(
            system_instruction=MASTER_SYSTEM_INSTRUCTION,
            tools=[{"google_search": {}}],
            safety_settings=UNRESTRICTED_SAFETY,
            temperature=0.7
        )
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=history_contents,
            config=config
        )
        reply_text = response.text or "कोई प्रतिक्रिया प्राप्त नहीं हुई।"

        user_conversations[user_id].append({"role": "user", "text": user_text})
        user_conversations[user_id].append({"role": "model", "text": reply_text})
        
        # Keep maximum 50 turns stored in file
        if len(user_conversations[user_id]) > 50:
            user_conversations[user_id] = user_conversations[user_id][-50:]
            
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
    caption = update.message.caption or "इस छवि का गहरा, बारीक और प्रोफेशनल विश्लेषण करें।"

    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    image = Image.open(io.BytesIO(photo_bytes))

    try:
        config = types.GenerateContentConfig(
            system_instruction=MASTER_SYSTEM_INSTRUCTION,
            safety_settings=UNRESTRICTED_SAFETY
        )
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=[image, caption],
            config=config
        )
        await update.message.reply_text(response.text or "विश्लेषण पूरा हुआ।")
    except Exception as e:
        await update.message.reply_text(f"विज़न विश्लेषण त्रुटि: {str(e)}")

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
            system_instruction=MASTER_SYSTEM_INSTRUCTION,
            safety_settings=UNRESTRICTED_SAFETY
        )
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=[audio_part, "इस ऑडियो संदेश को गहराई से समझें और सीधा, सटीक और व्यावहारिक समाधान दें।"],
            config=config
        )
        await update.message.reply_text(response.text or "ऑडियो प्रोसेस हो गया।")
    except Exception as e:
        await update.message.reply_text(f"ऑडियो प्रोसेसिंग त्रुटि: {str(e)}")

if __name__ == '__main__':
    print(f"Executive Super-Agent v2.0 (Full Power) Online on {CURRENT_MODEL}")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_memory))
    app.add_handler(CommandHandler("image", generate_image))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    
    app.run_polling()
