"""
Script pour lancer les deux bots simultanément - Version Expert
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from config.settings import BOT_USER_TOKEN, BOT_ADMIN_TOKEN
from database.connection import init_database, insert_default_testimonials, db

# Imports bot utilisateur
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

# Imports bot admin
from bot_admin.handlers.admin import (
    get_admin_handlers,
    handle_video_upload,
    handle_broadcast_message,
    handle_new_testimonial,
    handle_user_search,
    handle_custom_reject_message
)
from bot_admin.handlers.videos import get_video_admin_handlers
from bot_admin.handlers.help_videos import (
    get_help_videos_handlers,
    handle_help_video_upload,
    handle_help_video_edit
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============ ERROR HANDLER ============

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les erreurs"""
    logger.error(f"Exception: {context.error}")
    
    try:
        await db.ensure_connection()
    except:
        pass
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text("⚠️ Une erreur est survenue. Réessayez.")
        except:
            pass


# ============ BOT USER ============

async def handle_user_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les messages texte du bot utilisateur"""
    
    # Gestion des états conversation
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


async def run_user_bot():
    """Lance le bot utilisateur"""
    application = Application.builder().token(BOT_USER_TOKEN).build()
    
    # Handlers de commandes
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
    
    # Handler pour texte
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_text_message))
    
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Bot utilisateur démarré")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    return application


# ============ BOT ADMIN ============

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les messages du bot admin"""
    
    # Message de rejet personnalisé
    if context.user_data.get('waiting_custom_reject'):
        await handle_custom_reject_message(update, context)
        return
    
    # Upload vidéo d'aide
    if context.user_data.get('adding_help_video'):
        await handle_help_video_upload(update, context)
        return
    
    # Édition vidéo d'aide (titre/description)
    if context.user_data.get('editing_help_video_id'):
        await handle_help_video_edit(update, context)
        return
    
    if context.user_data.get('adding_video'):
        await handle_video_upload(update, context)
        return
    
    if context.user_data.get('broadcasting'):
        await handle_broadcast_message(update, context)
        return
    
    if context.user_data.get('adding_testimonial'):
        await handle_new_testimonial(update, context)
        return
    
    if context.user_data.get('searching_user'):
        await handle_user_search(update, context)
        return


async def run_admin_bot():
    """Lance le bot admin"""
    application = Application.builder().token(BOT_ADMIN_TOKEN).build()
    
    for handler in get_admin_handlers():
        application.add_handler(handler)
    
    # Handlers vidéo (nouveau système avec Cloudinary)
    for handler in get_video_admin_handlers():
        application.add_handler(handler)
    
    # Handlers vidéos d'aide
    for handler in get_help_videos_handlers():
        application.add_handler(handler)
    
    application.add_handler(
        MessageHandler(
            (filters.TEXT & ~filters.COMMAND) | filters.VIDEO | filters.Document.ALL,
            handle_admin_message
        )
    )
    
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Bot admin démarré")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    return application


# ============ KEEPALIVE DB ============

async def keepalive_db():
    """Garde la connexion DB active"""
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            await db.fetchval("SELECT 1")
            logger.info("💓 DB keepalive OK")
        except Exception as e:
            logger.error(f"❌ DB keepalive error: {e}")
            try:
                await db.ensure_connection()
            except:
                pass


# ============ MAIN ============

async def main():
    """Point d'entrée principal"""
    # Initialiser la base de données
    await init_database()
    await insert_default_testimonials()
    
    # Lancer les deux bots
    user_app = await run_user_bot()
    admin_app = await run_admin_bot()
    
    # Lancer le keepalive DB
    asyncio.create_task(keepalive_db())
    
    logger.info("✅ Les deux bots sont en cours d'exécution")
    logger.info("📌 Gestion vidéos via bot ADMIN: Menu → 📹 Vidéos")
    
    # Garder le script en vie
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Arrêt des bots...")
        
        await user_app.updater.stop()
        await user_app.stop()
        await user_app.shutdown()
        
        await admin_app.updater.stop()
        await admin_app.stop()
        await admin_app.shutdown()
        
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())