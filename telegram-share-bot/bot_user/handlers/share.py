"""
Handler pour la soumission des partages - Version avec Cloudinary
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    CallbackQueryHandler,
    MessageHandler,
    filters
)
import hashlib
from datetime import datetime

from database.queries import (
    get_user_by_telegram_id,
    get_active_video,
    get_active_testimonials,
    get_user_shares_today,
    create_share,
    get_video_by_id,
    check_duplicate_proof
)
from services.fraud_detector import validate_proof_image
from services.cloud_storage import upload_image_from_telegram, is_cloudinary_configured
from bot_user.keyboards.menus import (
    platform_selection_keyboard,
    back_keyboard,
    main_menu_keyboard
)
from utils.constants import ConversationState, Callback
from utils.helpers import normalize_link, is_valid_telegram_link, is_valid_whatsapp_link
from config.settings import (
    BOT_CHANNEL_LINK, 
    MAX_TELEGRAM_SHARES_PER_DAY,
    MAX_WHATSAPP_SHARES_PER_DAY,
    MIN_TELEGRAM_MEMBERS,
    MIN_WHATSAPP_MEMBERS
)


# ==================== ÉTAPE 1: CHOIX PLATEFORME ====================

async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /share - Démarre le processus de partage"""
    user = update.effective_user
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.message.delete()
        except:
            pass
    
    db_user = await get_user_by_telegram_id(user.id)
    if not db_user:
        await context.bot.send_message(
            chat_id=user.id,
            text="❌ Inscrivez-vous d'abord avec /start"
        )
        return
    
    video = await get_active_video()
    if not video:
        await context.bot.send_message(
            chat_id=user.id,
            text="❌ Aucune vidéo disponible actuellement.\nRevenez plus tard !",
            reply_markup=main_menu_keyboard()
        )
        return
    
    context.user_data.clear()
    context.user_data['video_id'] = video['id']
    
    await context.bot.send_message(
        chat_id=user.id,
        text="📤 <b>PARTAGER ET GAGNER 100 FCFA</b>\n\n"
             "Sur quelle plateforme allez-vous partager ?",
        reply_markup=platform_selection_keyboard(),
        parse_mode="HTML"
    )


# ==================== ÉTAPE 2: SÉLECTION TÉMOIGNAGE ====================

async def select_platform_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sélection de la plateforme"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)
    
    if query.data == Callback.PLATFORM_TELEGRAM:
        platform = "telegram"
        max_shares = MAX_TELEGRAM_SHARES_PER_DAY
    else:
        platform = "whatsapp"
        max_shares = MAX_WHATSAPP_SHARES_PER_DAY
    
    shares_today = await get_user_shares_today(db_user['id'], platform)
    if shares_today >= max_shares:
        await query.edit_message_text(
            f"❌ <b>Limite atteinte</b>\n\n"
            f"Vous avez déjà fait {max_shares} partages {platform.capitalize()} aujourd'hui.\n\n"
            f"Essayez l'autre plateforme ou revenez demain !",
            reply_markup=platform_selection_keyboard(),
            parse_mode="HTML"
        )
        return
    
    context.user_data['platform'] = platform
    
    # Afficher témoignages
    testimonials = await get_active_testimonials()
    
    keyboard = []
    for i, t in enumerate(testimonials, 1):
        preview = t['message'][:35] + "..." if len(t['message']) > 35 else t['message']
        keyboard.append([
            InlineKeyboardButton(f"{i}. {preview}", callback_data=f"testi_{t['id']}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("✏️ Écrire mon message", callback_data="testi_custom")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 Retour", callback_data="share")
    ])
    
    await query.edit_message_text(
        "💬 <b>ÉTAPE 1/4 - Choisir le témoignage</b>\n\n"
        "Ce message accompagnera votre partage.\n"
        "Choisissez-en un ou écrivez le vôtre :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ==================== ÉTAPE 3: AFFICHER CONTENU À PARTAGER ====================

async def select_testimonial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sélection du témoignage et affichage du contenu"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    
    if query.data == "testi_custom":
        context.user_data['state'] = ConversationState.WRITING_CUSTOM_TESTIMONIAL
        
        keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="share")]]
        await query.edit_message_text(
            "✏️ <b>Écrivez votre témoignage</b>\n\n"
            "Exemple : \"J'ai gagné 5000 FCFA en une semaine ! Rejoignez vite...\"\n\n"
            f"Le lien sera ajouté automatiquement : {BOT_CHANNEL_LINK}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return
    
    # Témoignage prédéfini
    testimonial_id = int(query.data.replace("testi_", ""))
    testimonials = await get_active_testimonials()
    testimonial = next((t for t in testimonials if t['id'] == testimonial_id), None)
    
    if testimonial:
        context.user_data['testimonial_text'] = testimonial['message'].format(link=BOT_CHANNEL_LINK)
    
    await show_share_content(update, context)


async def handle_custom_testimonial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Réception témoignage personnalisé"""
    if context.user_data.get('state') != ConversationState.WRITING_CUSTOM_TESTIMONIAL:
        return
    
    text = update.message.text.strip()
    
    if len(text) < 20:
        await update.message.reply_text("❌ Message trop court (min 20 caractères)")
        return
    
    if len(text) > 500:
        await update.message.reply_text("❌ Message trop long (max 500 caractères)")
        return
    
    # Ajouter le lien si absent
    if BOT_CHANNEL_LINK not in text:
        text = f"{text}\n\n👉 {BOT_CHANNEL_LINK}"
    
    context.user_data['testimonial_text'] = text
    context.user_data['state'] = None
    
    await show_share_content_from_message(update, context)


async def show_share_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le contenu à partager (depuis callback)"""
    query = update.callback_query
    user = update.effective_user
    
    try:
        await query.message.delete()
    except:
        pass
    
    await send_share_content(user.id, context)


async def show_share_content_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le contenu à partager (depuis message)"""
    await send_share_content(update.effective_user.id, context)


async def send_share_content(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Envoie le contenu à partager de manière organisée"""
    video = await get_video_by_id(context.user_data['video_id'])
    platform = context.user_data['platform']
    testimonial = context.user_data.get('testimonial_text', '')
    
    min_members = MIN_TELEGRAM_MEMBERS if platform == "telegram" else MIN_WHATSAPP_MEMBERS
    platform_name = "Telegram" if platform == "telegram" else "WhatsApp"
    
    # ===== MESSAGE 1: Instructions =====
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"📤 <b>ÉTAPE 2/4 - Partager le contenu</b>\n\n"
             f"📱 Plateforme : <b>{platform_name}</b>\n"
             f"👥 Groupe requis : <b>{min_members}+ membres</b>\n\n"
             f"━━━━━━━━━━━━━━━━━━\n\n"
             f"👇 <b>Suivez ces étapes :</b>\n\n"
             f"1️⃣ Transférez la vidéo ci-dessous\n"
             f"2️⃣ Copiez le témoignage\n"
             f"3️⃣ Envoyez les deux dans votre groupe\n"
             f"4️⃣ Faites une capture d'écran\n"
             f"5️⃣ Revenez soumettre votre preuve",
        parse_mode="HTML"
    )
    
    # ===== MESSAGE 2: Vidéo (transférable) =====
    video_url = video.get('cloud_url') or video.get('url')
    
    if video_url:
        try:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_url,
                caption=f"📹 <b>{video['title']}</b>\n\n{video['caption']}",
                parse_mode="HTML"
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Erreur vidéo : {str(e)[:50]}"
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📹 <b>{video['title']}</b>\n\n{video['caption']}",
            parse_mode="HTML"
        )
    
    # ===== MESSAGE 3: Témoignage (copiable) =====
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💬 <b>TÉMOIGNAGE À COPIER :</b>\n\n"
             f"━━━━━━━━━━━━━━━━━━\n\n"
             f"<code>{testimonial}</code>\n\n"
             f"━━━━━━━━━━━━━━━━━━\n\n"
             f"👆 <i>Appuyez longuement pour copier</i>",
        parse_mode="HTML"
    )
    
    # ===== MESSAGE 4: Bouton soumettre =====
    keyboard = [
        [InlineKeyboardButton("✅ J'ai partagé, soumettre ma preuve", callback_data="submit_proof")],
        [InlineKeyboardButton("❌ Annuler", callback_data="cancel_share")]
    ]
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="⬆️ <b>Partagez la vidéo et le témoignage dans votre groupe</b>\n\n"
             "Une fois fait, cliquez ci-dessous pour soumettre votre preuve :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ==================== ÉTAPE 4: SOUMETTRE PREUVE ====================

async def submit_proof_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demande la capture d'écran"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['state'] = ConversationState.WAITING_PROOF
    
    platform = context.user_data.get('platform', 'telegram')
    min_members = MIN_TELEGRAM_MEMBERS if platform == "telegram" else MIN_WHATSAPP_MEMBERS
    
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="cancel_share")]]
    
    await query.edit_message_text(
        f"📸 <b>ÉTAPE 3/4 - Capture d'écran</b>\n\n"
        f"Envoyez une capture d'écran montrant :\n\n"
        f"✅ La vidéo partagée dans le groupe\n"
        f"✅ Le nom du groupe visible\n"
        f"✅ Le nombre de membres ({min_members}+ requis)\n\n"
        f"📷 <b>Envoyez la capture maintenant :</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_proof_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Réception de la capture d'écran avec upload Cloudinary"""
    if context.user_data.get('state') != ConversationState.WAITING_PROOF:
        return
    
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)
    
    # Récupérer l'image
    if update.message.photo:
        photo = update.message.photo[-1]
        file_id = photo.file_id
    elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith('image/'):
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text("❌ Envoyez une image (photo ou fichier image).")
        return
    
    # Message de chargement
    loading_msg = await update.message.reply_text(
        "📤 <b>Traitement de votre preuve...</b>\n"
        "⏳ Veuillez patienter...",
        parse_mode="HTML"
    )
    
    try:
        # Télécharger le fichier pour calculer le hash et valider
        file = await context.bot.get_file(file_id)
        image_data = await file.download_as_bytearray()
        image_bytes = bytes(image_data)
        
        # Calculer le hash
        proof_hash = hashlib.sha256(image_bytes).hexdigest()
        
        # Vérifier si preuve déjà soumise
        if await check_duplicate_proof(proof_hash):
            await loading_msg.edit_text(
                "❌ <b>Preuve déjà utilisée</b>\n\n"
                "Cette image a déjà été soumise. Utilisez une nouvelle capture.",
                parse_mode="HTML"
            )
            return
        
        platform = context.user_data.get('platform', 'telegram')
        
        # Valider l'image
        result, _ = await validate_proof_image(
            image_bytes,
            db_user['id'],
            "",
            platform
        )
        
        if not result.is_valid:
            keyboard = [[InlineKeyboardButton("🔄 Réessayer", callback_data="submit_proof")]]
            await loading_msg.edit_text(
                f"❌ <b>Preuve invalide</b>\n\n{result.error}\n\nRéessayez avec une meilleure capture.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            return
        
        # Upload vers Cloudinary si configuré
        proof_image_url = None
        proof_cloud_public_id = None
        
        if is_cloudinary_configured():
            await loading_msg.edit_text(
                "☁️ <b>Upload vers le cloud...</b>\n"
                "⏳ Cela peut prendre quelques secondes...",
                parse_mode="HTML"
            )
            
            upload_result = await upload_image_from_telegram(
                context.bot,
                file_id,
                f"proof_{db_user['id']}_{int(datetime.now().timestamp())}"
            )
            
            if upload_result['success']:
                proof_image_url = upload_result['url']
                proof_cloud_public_id = upload_result['public_id']
                
                await loading_msg.edit_text(
                    "✅ <b>Image uploadée avec succès !</b>\n"
                    "📝 Continuons...",
                    parse_mode="HTML"
                )
            else:
                # Log l'erreur mais continue
                print(f"⚠️ Erreur upload Cloudinary : {upload_result.get('error')}")
                await loading_msg.edit_text(
                    "⚠️ <b>Upload cloud échoué</b>\n"
                    "La preuve sera enregistrée localement.\n"
                    "Continuons...",
                    parse_mode="HTML"
                )
        else:
            await loading_msg.edit_text(
                "⚠️ <b>Cloud non configuré</b>\n"
                "La preuve sera enregistrée avec le file_id.\n"
                "Continuons...",
                parse_mode="HTML"
            )
        
        # Stocker les données
        context.user_data['proof_file_id'] = file_id
        context.user_data['proof_hash'] = proof_hash
        context.user_data['proof_image_url'] = proof_image_url
        context.user_data['proof_cloud_public_id'] = proof_cloud_public_id
        context.user_data['state'] = ConversationState.WAITING_GROUP_LINK
        
        platform_name = "Telegram" if platform == "telegram" else "WhatsApp"
        
        if platform == "telegram":
            example = "https://t.me/nomdugroupe ou @nomdugroupe"
        else:
            example = "https://chat.whatsapp.com/..."
        
        keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="cancel_share")]]
        
        await loading_msg.edit_text(
            f"✅ <b>Capture reçue et validée !</b>\n\n"
            f"📎 <b>ÉTAPE 4/4 - Lien du groupe</b>\n\n"
            f"Envoyez le lien du groupe {platform_name} :\n\n"
            f"<i>Exemple : {example}</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        
    except Exception as e:
        await loading_msg.edit_text(
            f"❌ <b>Erreur</b>\n\n"
            f"Une erreur s'est produite : {str(e)[:100]}\n\n"
            f"Réessayez ou contactez le support.",
            parse_mode="HTML"
        )
        print(f"❌ Erreur lors du traitement de la preuve : {e}")
        import traceback
        traceback.print_exc()


async def handle_group_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Réception du lien du groupe"""
    if context.user_data.get('state') != ConversationState.WAITING_GROUP_LINK:
        return
    
    link = update.message.text.strip()
    platform = context.user_data.get('platform', 'telegram')
    
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="cancel_share")]]
    
    if platform == "telegram":
        if not is_valid_telegram_link(link):
            await update.message.reply_text(
                "❌ Lien Telegram invalide.\n\n"
                "Exemple : https://t.me/groupe ou @groupe",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    else:
        if not is_valid_whatsapp_link(link):
            await update.message.reply_text(
                "❌ Lien WhatsApp invalide.\n\n"
                "Exemple : https://chat.whatsapp.com/...",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    
    context.user_data['group_link'] = normalize_link(link)
    context.user_data['state'] = ConversationState.WAITING_GROUP_NAME
    
    await update.message.reply_text(
        "✅ <b>Lien reçu !</b>\n\n"
        "📝 <b>Dernière étape</b> - Nom du groupe :\n\n"
        "Entrez le nom exact du groupe :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Réception du nom et finalisation"""
    if context.user_data.get('state') != ConversationState.WAITING_GROUP_NAME:
        return
    
    group_name = update.message.text.strip()
    
    if len(group_name) < 3:
        await update.message.reply_text("❌ Nom trop court. Entrez le nom complet.")
        return
    
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)
    
    # Message de finalisation
    final_msg = await update.message.reply_text(
        "⏳ <b>Finalisation...</b>",
        parse_mode="HTML"
    )
    
    try:
        # Créer le partage avec toutes les infos
        share = await create_share(
            user_id=db_user['id'],
            video_id=context.user_data['video_id'],
            platform=context.user_data['platform'],
            proof_image_file_id=context.user_data['proof_file_id'],
            proof_image_hash=context.user_data['proof_hash'],
            proof_image_url=context.user_data.get('proof_image_url'),
            proof_cloud_public_id=context.user_data.get('proof_cloud_public_id'),
            group_name=group_name,
            group_link=context.user_data['group_link'],
            testimonial_id=None,
            custom_testimonial=context.user_data.get('testimonial_text')
        )
        
        platform_name = "Telegram" if context.user_data['platform'] == "telegram" else "WhatsApp"
        
        keyboard = [
            [InlineKeyboardButton("📤 Faire un autre partage", callback_data="share")],
            [InlineKeyboardButton("💰 Mon solde", callback_data="balance")],
            [InlineKeyboardButton("🏠 Menu principal", callback_data="main_menu")]
        ]
        
        await final_msg.edit_text(
            f"🎉 <b>PARTAGE SOUMIS AVEC SUCCÈS !</b>\n\n"
            f"📋 Référence : #{share['id']}\n"
            f"📱 Plateforme : {platform_name}\n"
            f"👥 Groupe : {group_name}\n"
            f"🔗 {context.user_data['group_link']}\n\n"
            f"⏳ <b>En attente de validation</b>\n\n"
            f"Un admin vérifiera votre preuve.\n"
            f"Vous serez notifié et recevrez <b>100 FCFA</b> si approuvé !",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        
        # Nettoyer
        context.user_data.clear()
        
    except Exception as e:
        await final_msg.edit_text(
            f"❌ <b>Erreur lors de la soumission</b>\n\n"
            f"{str(e)[:100]}\n\n"
            f"Contactez le support avec cette erreur.",
            parse_mode="HTML"
        )
        print(f"❌ Erreur création partage : {e}")
        import traceback
        traceback.print_exc()


async def cancel_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annule le processus de partage"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.clear()
    
    await query.edit_message_text(
        "❌ Partage annulé.",
        reply_markup=main_menu_keyboard()
    )


def get_share_handlers():
    """Retourne les handlers pour les partages"""
    return [
        CommandHandler("share", share_command),
        CallbackQueryHandler(share_command, pattern="^share$"),
        CallbackQueryHandler(select_platform_callback, pattern=f"^{Callback.PLATFORM_TELEGRAM}$|^{Callback.PLATFORM_WHATSAPP}$"),
        CallbackQueryHandler(select_testimonial_callback, pattern=r"^testi_"),
        CallbackQueryHandler(submit_proof_callback, pattern="^submit_proof$"),
        CallbackQueryHandler(cancel_share_callback, pattern="^cancel_share$"),
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_proof_image),
    ]