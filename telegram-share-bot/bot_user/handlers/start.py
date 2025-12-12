"""
Handler de démarrage et inscription
"""
from telegram import Update
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters
)

from database.queries import (
    create_user, 
    get_user_by_telegram_id, 
    update_user_phone,
    update_user_last_active
)
from bot_user.keyboards.menus import (
    main_menu_keyboard, 
    phone_request_keyboard,
    remove_keyboard
)
from utils.constants import (
    WELCOME_MESSAGE, 
    PHONE_REQUEST_MESSAGE, 
    REGISTRATION_SUCCESS_MESSAGE,
    ERROR_USER_BLOCKED,
    ConversationState
)
from config.settings import BOT_CHANNEL_LINK


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start - Inscription ou accueil"""
    user = update.effective_user
    telegram_id = user.id
    
    # Extraire le code de parrainage si présent
    referral_code = None
    if context.args:
        referral_code = context.args[0]
    
    # Vérifier si l'utilisateur existe déjà
    existing_user = await get_user_by_telegram_id(telegram_id)
    
    if existing_user:
        # Utilisateur existant
        if existing_user['is_blocked']:
            await update.message.reply_text(ERROR_USER_BLOCKED)
            return
        
        # Mettre à jour la dernière activité
        await update_user_last_active(telegram_id)
        
        # Afficher le menu principal
        await update.message.reply_text(
            f"👋 Rebonjour <b>{user.first_name}</b> !\n\n"
            f"💰 Solde : <b>{existing_user['balance']} FCFA</b>\n\n"
            "Que souhaitez-vous faire ?",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Nouvel utilisateur - Afficher le message de bienvenue
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode="HTML"
    )
    
    # Demander le numéro de téléphone
    await update.message.reply_text(
        PHONE_REQUEST_MESSAGE,
        reply_markup=phone_request_keyboard(),
        parse_mode="HTML"
    )
    
    # Stocker le code de parrainage temporairement
    context.user_data['referral_code'] = referral_code
    context.user_data['state'] = ConversationState.WAITING_PHONE


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la réception du contact (numéro de téléphone)"""
    contact = update.message.contact
    user = update.effective_user
    
    if not contact:
        await update.message.reply_text(
            "❌ Veuillez partager votre numéro via le bouton.",
            reply_markup=phone_request_keyboard()
        )
        return
    
    phone = contact.phone_number
    referral_code = context.user_data.get('referral_code')
    
    # Créer l'utilisateur
    new_user = await create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        referred_by_code=referral_code
    )
    
    # Mettre à jour le numéro de téléphone
    await update_user_phone(user.id, phone)
    
    # Supprimer le clavier de contact
    await update.message.reply_text(
        "✅ Numéro enregistré !",
        reply_markup=remove_keyboard()
    )
    
    # Message de succès
    await update.message.reply_text(
        REGISTRATION_SUCCESS_MESSAGE.format(
            referral_code=new_user['referral_code']
        ),
        parse_mode="HTML"
    )
    
    # Afficher le menu principal
    await update.message.reply_text(
        "🎯 <b>Commencez à gagner maintenant !</b>\n\n"
        "Que souhaitez-vous faire ?",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    
    # Nettoyer les données temporaires
    context.user_data.clear()


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback pour retourner au menu principal"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)
    
    if not db_user:
        try:
            await query.edit_message_text(
                "❌ Vous devez d'abord vous inscrire.\nTapez /start"
            )
        except:
            await query.message.reply_text(
                "❌ Vous devez d'abord vous inscrire.\nTapez /start"
            )
        return
    
    menu_text = (
        f"👋 <b>{user.first_name}</b>\n\n"
        f"💰 Solde : <b>{db_user['balance']} FCFA</b>\n\n"
        "Que souhaitez-vous faire ?"
    )
    
    try:
        # Essayer d'éditer le message (fonctionne pour les messages texte)
        await query.edit_message_text(
            menu_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        # Si échec (message vidéo/photo), supprimer et envoyer un nouveau
        try:
            await query.message.delete()
        except:
            pass
        
        await context.bot.send_message(
            chat_id=user.id,
            text=menu_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    
    # Nettoyer les données de conversation
    context.user_data.clear()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /help - Affiche l'aide avec les vidéos tutorielles"""
    from utils.constants import HELP_MESSAGE
    from bot_user.keyboards.menus import back_keyboard
    from database.queries import get_help_videos
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # Récupérer les vidéos d'aide actives
    help_videos = await get_help_videos(active_only=True)
    
    # Construire le texte et le clavier
    text = HELP_MESSAGE
    
    keyboard = []
    
    if help_videos:
        text += "\n\n📚 <b>Vidéos tutorielles :</b>\n"
        text += "<i>Cliquez sur une vidéo pour la regarder</i>\n"
        
        for video in help_videos:
            keyboard.append([
                InlineKeyboardButton(
                    f"🎬 {video['title']}",
                    callback_data=f"watch_help_{video['id']}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🏠 Menu principal", callback_data="main_menu")])
    
    if update.callback_query:
        await update.callback_query.answer()
        try:
            # Essayer d'éditer (fonctionne pour les messages texte)
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except Exception as e:
            # Si échec (message vidéo/photo), supprimer et envoyer un nouveau
            try:
                await update.callback_query.message.delete()
            except:
                pass
            
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )


async def watch_help_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche une vidéo d'aide"""
    from database.queries import get_help_video_by_id, increment_help_video_views
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    query = update.callback_query
    await query.answer()
    
    video_id = int(query.data.replace("watch_help_", ""))
    video = await get_help_video_by_id(video_id)
    
    if not video:
        await query.edit_message_text(
            "❌ Vidéo non disponible.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Retour à l'aide", callback_data="help")
            ]])
        )
        return
    
    # Incrémenter les vues
    await increment_help_video_views(video_id)
    
    # Préparer le texte
    caption = f"📹 <b>{video['title']}</b>\n\n"
    if video['description']:
        caption += f"{video['description']}\n\n"
    caption += "💡 <i>Cette vidéo vous aide à mieux comprendre le fonctionnement du bot.</i>"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Retour à l'aide", callback_data="help")],
        [InlineKeyboardButton("🏠 Menu principal", callback_data="main_menu")]
    ])
    
    # Supprimer l'ancien message
    try:
        await query.message.delete()
    except:
        pass
    
    # Envoyer la vidéo
    video_source = video.get('cloud_url') or video.get('video_url') or video.get('video_file_id')
    
    if video_source:
        try:
            await context.bot.send_video(
                chat_id=query.from_user.id,
                video=video_source,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            # Si l'envoi de vidéo échoue, essayer comme lien
            if video.get('video_url'):
                text = f"{caption}\n\n🔗 <a href=\"{video['video_url']}\">Cliquer pour voir la vidéo</a>"
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )
            else:
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text=f"❌ Impossible de charger la vidéo.\n\n{caption}",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
    else:
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"❌ Vidéo non configurée.\n\n{caption}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )


def get_start_handlers():
    """Retourne les handlers de démarrage"""
    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        MessageHandler(filters.CONTACT, handle_contact),
        CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"),
        CallbackQueryHandler(help_command, pattern="^help$"),
        CallbackQueryHandler(watch_help_video, pattern="^watch_help_\\d+$"),
    ]