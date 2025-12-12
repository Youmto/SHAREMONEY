"""
Bot Utilisateur - Point d'entrée principal
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes
)

from config.settings import BOT_USER_TOKEN
from database.connection import init_database, insert_default_testimonials, db
from bot_user.handlers import (
    get_start_handlers,
    get_video_handlers,
    get_share_handlers,
    get_balance_handlers,
    get_withdraw_handlers,
    get_referral_handlers,
    handle_custom_testimonial,
    handle_group_link,
    handle_group_name,
    handle_payment_details,
    handle_custom_amount
)
from utils.constants import ConversationState

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère tous les messages texte selon l'état de conversation"""
    state = context.user_data.get('state')
    
    if state == ConversationState.WRITING_CUSTOM_TESTIMONIAL:
        await handle_custom_testimonial(update, context)
    elif state == ConversationState.WAITING_GROUP_LINK:
        await handle_group_link(update, context)
    elif state == ConversationState.WAITING_GROUP_NAME:
        await handle_group_name(update, context)
    elif state == ConversationState.WAITING_PAYMENT_DETAILS:
        await handle_payment_details(update, context)
    elif state == ConversationState.WAITING_AMOUNT:
        await handle_custom_amount(update, context)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les erreurs"""
    logger.error(f"Exception: {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Une erreur est survenue. Veuillez réessayer ou taper /start"
        )


async def post_init(application: Application):
    """Actions après initialisation"""
    await init_database()
    await insert_default_testimonials()
    logger.info("✅ Bot utilisateur initialisé")


async def post_shutdown(application: Application):
    """Actions avant arrêt"""
    await db.disconnect()
    logger.info("🔌 Bot utilisateur arrêté")


def main():
    """Fonction principale"""
    application = (
        Application.builder()
        .token(BOT_USER_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Ajouter les handlers
    for handler in get_start_handlers():
        application.add_handler(handler)
    
    for handler in get_video_handlers():
        application.add_handler(handler)
    
    for handler in get_share_handlers():
        application.add_handler(handler)
    
    for handler in get_balance_handlers():
        application.add_handler(handler)
    
    for handler in get_withdraw_handlers():
        application.add_handler(handler)
    
    for handler in get_referral_handlers():
        application.add_handler(handler)
    
    # Handler pour les messages texte
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )
    
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Démarrage du bot utilisateur...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
