import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from rin.core import Assistant
from rin.config import TELEGRAM_BOT_TOKEN
from rin.logging_config import loggers

logger = loggers.get('core', logging.getLogger('rin.telegram'))

class RinTelegramBot:
    """Telegram bot integration for Rin"""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not found. Telegram bot functionality disabled.")
            return
        
        self.assistant = Assistant()
        logger.info("Telegram Bot initialized")
    
    async def start(self):
        """Start the Telegram bot"""
        if not self.token:
            logger.error("Cannot start Telegram bot: No token provided")
            return False
        
        try:
            # Create the application
            application = ApplicationBuilder().token(self.token).build()
            
            # Add handlers
            application.add_handler(CommandHandler("start", self.start_command))
            application.add_handler(CommandHandler("help", self.help_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Start the bot - the proper way to run polling
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            
            # Keep the bot running until a shutdown is requested
            logger.info("Telegram bot is running. Press Ctrl+C to stop.")
            
            # Wait for a termination signal
            stop_signal = asyncio.Future()
            
            try:
                await stop_signal
            except asyncio.CancelledError:
                pass
            finally:
                # Shutdown properly
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
                
            return True
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {str(e)}")
            return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "👋 Hello! I'm Rin, your personal assistant. Ask me anything!"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
*Rin Assistant Bot*

You can ask me questions, and I'll do my best to help!

*Commands:*
/start - Start the conversation
/help - Show this help message

Just type your questions or requests normally, and I'll respond.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        logger.info(f"Telegram message from {user_id}: {user_message}")
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Process the message with Rin
            response = await self.assistant.process_query(user_message)
            
            # Send the response
            await update.message.reply_text(response.get("text", "I'm not sure how to respond to that."))
        except Exception as e:
            logger.error(f"Error processing Telegram message: {str(e)}")
            await update.message.reply_text("Sorry, I encountered an error while processing your request.") 