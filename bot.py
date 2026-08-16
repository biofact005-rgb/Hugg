import telebot
import google.generativeai as genai
from PIL import Image
import io
import os
import sys
import threading
from flask import Flask

# ================= K E Y S (From Environment) ================= #
# Ab keys direct code me nahi hain, balki Render ke environment se aayengi
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Check agar keys miss ho jayein
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    print("⚠️ ERROR: Tokens missing! Kripya Render me Environment Variables check karein.")
    sys.exit()

# ================= RENDER WEB SERVER ================= #
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running perfectly on Render!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= BOT SETUP ================= #
bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

system_prompt = (
    "Tum ek professional aur expert NEET faculty ho. "
    "Tumhara kaam students ke Physics, Chemistry aur Biology ke doubts clear karna hai. "
    "Answers step-by-step, to-the-point aur easy to understand hone chahiye. "
    "Hamesha NCERT ke concepts ko priority dena."
)

model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=system_prompt)

try:
    bot_info = bot.get_me()
    BOT_USERNAME = bot_info.username
    print(f"Bot Started Successfully! Username: @{BOT_USERNAME}")
except Exception as e:
    print("Error starting bot. Token check karein!", e)

def is_bot_mentioned(message):
    if message.chat.type == 'private':
        return True
    if message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id:
        return True
    text_to_check = message.text or message.caption or ""
    if f"@{BOT_USERNAME}" in text_to_check:
        return True
    return False

@bot.message_handler(content_types=['text', 'photo'])
def handle_queries(message):
    if not is_bot_mentioned(message):
        return

    status_msg = bot.reply_to(message, "⏳ Check kar raha hu, thoda wait karo...")

    try:
        raw_text = message.text or message.caption or ""
        user_query = raw_text.replace(f"@{BOT_USERNAME}", "").strip()
        
        if not user_query and not message.photo:
            bot.edit_message_text("Sawal puchne ke liye kuch type karein ya photo bhejein.", 
                                  chat_id=message.chat.id, message_id=status_msg.message_id)
            return

        if message.photo:
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            image = Image.open(io.BytesIO(downloaded_file))
            
            prompt_parts = [image]
            if user_query:
                prompt_parts.append(user_query)
            else:
                prompt_parts.append("Is image me diye gaye question ko explain karo.")
                
            response = model.generate_content(prompt_parts)
        else:
            response = model.generate_content(user_query)

        final_answer = response.text[:4000]
        bot.edit_message_text(final_answer, chat_id=message.chat.id, message_id=status_msg.message_id)

    except Exception as e:
        print(f"Error: {e}")
        bot.edit_message_text("⚠️ Kuch error aagaya. Shayad limit khatam ho gayi ya sawal samajh nahi aaya.", 
                              chat_id=message.chat.id, message_id=status_msg.message_id)

# ================= START APPLICATION ================= #
if __name__ == "__main__":
    # Server ko alag thread me start karna taki bot block na ho
    server_thread = threading.Thread(target=run_server)
    server_thread.start()
    
    # Bot ko start karna
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
