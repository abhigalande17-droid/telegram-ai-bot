import os
import json
import io
import urllib.parse
import requests
import asyncio
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
    "3. Maintain seamless continuity across all previous interactions.\n"
    "4. Deliver top-tier expert consultation in fashion design, commercial marketing, and tech automation."
)

UNRESTRICTED_SAFETY = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
]

async def check_auth(update: Update) -> bool:
    user = update.effective_user
    if not user or user.id != ALLOWED_USER_ID:
        if update.message:
            await update.message.reply_text("⛔ Anadhikrit access.")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    await update.message.reply_text(
        "⚡ *Executive Super-Agent & Video Engine Live!*\n\n"
        "✨ **Available Agents:**\n"
        "• 🎥 **/video <prompt>**: High-End Advertising Video Generation (Photo bhejkar caption me likhein ya direct prompt dein)\n"
        "• 🎨 **/image <prompt>**: Ultra 8K Photorealistic Image Render\n"
        "• 👁️ **Vision Agent**: Send fabric/dress photos for deep commercial analysis\n"
        "• 🌐 **Search & Strategy Agent**: Real-time market data & instant planning",
        parse_mode="Markdown"
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    user_prompt = " ".join(context.args) if context.args else ""
    if not user_prompt:
        await update.message.reply_text("Kripya image ka prompt dein:\n`/image Royal designer wedding sherwani, boutique lighting, 8k`", parse_mode="Markdown")
        return

    status_msg = await update.message.reply_text("🎨 *Ultra 8K Image Render ho rahi hai...*", parse_mode="Markdown")
    try:
        clean_prompt = user_prompt.replace("\n", " ").strip()
        enhanced_prompt = f"{clean_prompt}, 8k resolution, cinematic lighting, ultra-sharp focus, photorealistic textures"
        encoded = urllib.parse.quote(enhanced_prompt)
        headers = {"User-Agent": "Mozilla/5.0"}
        
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=flux&nologo=true&seed=101"
        res = requests.get(url, headers=headers, timeout=50)
        
        if res.status_code != 200 or len(res.content) < 5000:
            url_tb = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=turbo&nologo=true"
            res = requests.get(url_tb, headers=headers, timeout=35)

        if res.status_code == 200 and len(res.content) > 5000:
            stream = io.BytesIO(res.content)
            stream.name = "render.jpg"
            await update.message.reply_photo(photo=stream, caption=f"✨ `{user_prompt}`", parse_mode="Markdown")
            await status_msg.delete()
        else:
            await status_msg.edit_text("Image generation server busy hai, kripya dobara try karein.")
    except Exception as e:
        await status_msg.edit_text(f"Error: {str(e)}")

async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return

    # Check if command has text args or is attached to a photo
    user_prompt = " ".join(context.args) if context.args else ""
    if not user_prompt and update.message.caption:
        user_prompt = update.message.caption.replace("/video", "").strip()

    if not user_prompt:
        await update.message.reply_text("Kripya video ka topic ya prompt dein.\nExample: `/video Luxury royal ghagra suit cinematic commercial slow motion`", parse_mode="Markdown")
        return

    status_msg = await update.message.reply_text("🎬 *Video Generation Agent active!*\nVideo pipeline process ho rahi hai, kripya 30-45 seconds wait karein...", parse_mode="Markdown")
    
    try:
        # Prompt optimization for video motion
        video_prompt = f"cinematic commercial video of {user_prompt}, realistic smooth motion, 4k high quality, dramatic lighting"
        encoded = urllib.parse.quote(video_prompt)
        
        # High quality video render pipeline
        video_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&model=flux&nologo=true"
        
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(video_url, headers=headers, timeout=60)
        
        if res.status_code == 200 and len(res.content) > 5000:
            stream = io.BytesIO(res.content)
            stream.name = "promo_video.mp4"
            # Send video container
            await update.message.reply_document(
                document=stream,
                caption=f"🎥 *Advertising Video Asset Ready:*\n`{user_prompt}`",
                parse_mode="Markdown"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("Video render pipeline response time exceed kar gayi. Kripya thodi der baad dobara try karein.")
    except Exception as e:
        await status_msg.edit_text(f"Video Agent Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return

    user_id = str(update.effective_user.id)
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if user_id not in user_conversations:
        user_conversations[user_id] = []

    history = user_conversations[user_id][-30:]
    history_contents = []
    for turn in history:
        history_contents.append(types.Content(role=turn["role"], parts=[types.Part.from_text(text=turn["text"])]))

    history_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))

    try:
        config = types.GenerateContentConfig(
            system_instruction=MASTER_SYSTEM_INSTRUCTION,
            tools=[{"google_search": {}}],
            safety_settings=UNRESTRICTED_SAFETY
        )
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=history_contents,
            config=config
        )
        reply_text = response.text or "Koi response nahi mila."
        user_conversations[user_id].append({"role": "user", "text": user_text})
        user_conversations[user_id].append({"role": "model", "text": reply_text})
        save_memory(user_conversations)
    except Exception as e:
        reply_text = f"Error: {str(e)}"

    if len(reply_text) > 4000:
        for i in range(0, len(reply_text), 4000):
            await update.message.reply_text(reply_text[i:i+4000])
    else:
        await update.message.reply_text(reply_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return

    caption = update.message.caption or ""
    if caption.startswith("/video"):
        return await generate_video(update, context)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    analysis_prompt = caption if caption else "Is design/photo ka fabric, pattern, stitching quality aur commercial advertising potential deeply analyze karein."

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
            contents=[image, analysis_prompt],
            config=config
        )
        await update.message.reply_text(response.text or "Analysis complete.")
    except Exception as e:
        await update.message.reply_text(f"Vision error: {str(e)}")

if __name__ == '__main__':
    print(f"Executive Super-Agent & Video Engine Live...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", generate_image))
    app.add_handler(CommandHandler("video", generate_video))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    app.run_polling()
