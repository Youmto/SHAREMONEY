"""
Bot Admin - Point d'entrée principal
"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes
)

from config.settings import BOT_ADMIN_TOKEN
from database.connection import init_database, db
from bot_admin.handlers import (
    get_admin_handlers,
    handle_video_upload,
    handle_broadcast_message,
    handle_new_testimonial,
    handle_user_search
)

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les messages texte et vidéos pour l'admin"""
    
    # Gestion upload vidéo
    if context.user_data.get('adding_video'):
        await handle_video_upload(update, context)
        return
    
    # Gestion broadcast
    if context.user_data.get('broadcasting'):
        await handle_broadcast_message(update, context)
        return
    
    # Gestion ajout témoignage
    if context.user_data.get('adding_testimonial'):
        await handle_new_testimonial(update, context)
        return
    
    # Gestion recherche utilisateur
    if context.user_data.get('searching_user'):
        await handle_user_search(update, context)
        return


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les erreurs"""
    logger.error(f"Exception: {context.error}", exc_info=context.error)


async def post_init(application: Application):
    """Actions après initialisation"""
    await init_database()
    logger.info("✅ Bot admin initialisé")


async def post_shutdown(application: Application):
    """Actions avant arrêt"""
    await db.disconnect()
    logger.info("🔌 Bot admin arrêté")


def main():
    """Fonction principale"""
    application = (
        Application.builder()
        .token(BOT_ADMIN_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Ajouter les handlers admin
    for handler in get_admin_handlers():
        application.add_handler(handler)
    
    # Handler pour messages (vidéo, texte broadcast)
    application.add_handler(
        MessageHandler(
            (filters.TEXT & ~filters.COMMAND) | filters.VIDEO,
            handle_admin_message
        )
    )
    
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Démarrage du bot admin...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
