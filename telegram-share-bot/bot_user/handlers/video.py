"""
Handler vidéo pour les utilisateurs
Affiche la vidéo du jour via URL cloud
"""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from database.queries import get_user_by_telegram_id, get_active_video
from bot_user.keyboards.menus import video_keyboard, main_menu_keyboard


async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la vidéo du jour"""
    user = update.effective_user
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        is_callback = True
    else:
        is_callback = False
    
    db_user = await get_user_by_telegram_id(user.id)
    if not db_user:
        text = "❌ Inscrivez-vous d'abord avec /start"
        if is_callback:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return
    
    video = await get_active_video()
    
    if not video:
        text = "📹 <b>Aucune vidéo disponible</b>\n\nRevenez plus tard !"
        if is_callback:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
        return
    
    # Temps restant
    remaining = video['expires_at'] - datetime.now()
    hours_left = max(0, int(remaining.total_seconds() // 3600))
    
    if is_callback:
        try:
            await query.message.delete()
        except:
            pass
    
    caption = f"""
📹 <b>{video['title']}</b>

{video['caption']}

⏱️ <b>Expire dans {hours_left}h</b>

💰 Partagez pour gagner <b>100 FCFA</b> !
"""
    
    # URL de la vidéo (cloud ou externe)
    video_url = video.get('cloud_url') or video.get('url')
    
    try:
        if video_url:
            await context.bot.send_video(
                chat_id=user.id,
                video=video_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=video_keyboard()
            )
        else:
            await context.bot.send_message(
                chat_id=user.id,
                text="❌ Vidéo non disponible.",
                reply_markup=main_menu_keyboard()
            )
    except Exception as e:
        print(f"❌ Erreur envoi vidéo: {e}")
        await context.bot.send_message(
            chat_id=user.id,
            text="❌ Erreur lors de l'envoi de la vidéo.\nRéessayez plus tard.",
            reply_markup=main_menu_keyboard()
        )


def get_video_handlers():
    """Handlers vidéo utilisateur"""
    return [
        CommandHandler("video", video_command),
        CallbackQueryHandler(video_command, pattern="^video$"),
    ]