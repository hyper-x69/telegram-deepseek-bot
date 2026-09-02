import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TELEGRAM_BOT_TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN or DEEPSEEK_API_KEY")

# Conversation history (simple in-memory storage)
user_histories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user_id = update.message.from_user.id
    user_histories[user_id] = []  # Initialize conversation history
    
    await update.message.reply_text(
        "🤖 হ্যালো! আমি DeepSeek AI দ্বারা চালিত একটি বট।\n\n"
        "আমাকে যেকোনো প্রশ্ন জিজ্ঞাসা করুন এবং আমি উত্তর দেব।\n\n"
        "/clear - আমাদের কথোপকথন রিসেট করুন\n"
        "/help - সাহায্য পান"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    await update.message.reply_text(
        "আমি DeepSeek AI বট। আমি:\n"
        "• প্রশ্নর উত্তর দিতে পারি\n"
        "• গল্প বলতে পারি\n"
        "• কড লিখতে পারি\n"
        "• যেকোনো কিছু ব্যাখ্যা করতে পারি\n\n"
        "শুধু আমাকে কছু বলুন!"
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history"""
    user_id = update.message.from_user.id
    user_histories[user_id] = []
    await update.message.reply_text("✅ কথোপকথন পরিষ্কার করা হয়েছে!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    user_id = update.message.from_user.id
    user_message = update.message.text
    
    # Initialize history if new user
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    # Show typing indicator
    await update.message.chat.send_action("typing")
    
    try:
        # Add user message to history
        user_histories[user_id].append({"role": "user", "content": user_message})
        
        # Keep only last 10 messages (to avoid token limits)
        if len(user_histories[user_id]) > 10:
            user_histories[user_id] = user_histories[user_id][-10:]
        
        # Call DeepSeek API
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": user_histories[user_id],
                "temperature": 0.7,
                "max_tokens": 1024
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            
            # Add assistant response to history
            user_histories[user_id].append({"role": "assistant", "content": reply})
            
            # Split long messages (Telegram limit: 4096 chars)
            if len(reply) > 4096:
                for i in range(0, len(reply), 4096):
                    await update.message.reply_text(reply[i:i+4096])
            else:
                await update.message.reply_text(reply)
        else:
            error_msg = response.json().get("error", {}).get("message", "Unknown error")
            await update.message.reply_text(f"❌ API Error: {error_msg}")
    
    except requests.Timeout:
        await update.message.reply_text("⏱️ Request timeout. Try again.")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

def main():
    """Start the bot"""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    logger.info("Bot started (polling mode)")
    app.run_polling()

if __name__ == "__main__":
    main()
