"""
Gestion des vidéos d'aide - Admin
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

from database.queries import (
    get_help_videos,
    get_help_video_by_id,
    create_help_video,
    update_help_video,
    delete_help_video,
    toggle_help_video,
    reorder_help_video
)
from bot_admin.keyboards.admin_menus import back_to_menu_keyboard
from bot_admin.handlers.admin import admin_required
from services.cloud_storage import upload_video_from_telegram, is_cloudinary_configured


# ==================== LISTE DES VIDÉOS D'AIDE ====================

async def help_videos_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le menu de gestion des vidéos d'aide"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    videos = await get_help_videos(active_only=False)
    
    text = "📚 <b>Vidéos d'aide</b>\n\n"
    
    if videos:
        for i, v in enumerate(videos, 1):
            status = "✅" if v['is_active'] else "❌"
            views = v.get('views_count', 0)
            text += f"{i}. {status} <b>{v['title']}</b>\n"
            text += f"   👁 {views} vues | 📍 Ordre: {v['display_order']}\n\n"
    else:
        text += "📭 Aucune vidéo d'aide configurée.\n\n"
    
    text += "💡 <i>Les vidéos aident les utilisateurs à comprendre le fonctionnement du bot.</i>"
    
    keyboard = [
        [InlineKeyboardButton("➕ Ajouter une vidéo", callback_data="add_help_video")],
    ]
    
    if videos:
        keyboard.append([InlineKeyboardButton("📝 Gérer les vidéos", callback_data="manage_help_videos")])
    
    keyboard.append([InlineKeyboardButton("🏠 Menu principal", callback_data="admin_menu")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def manage_help_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la liste des vidéos à gérer"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    videos = await get_help_videos(active_only=False)
    
    if not videos:
        await query.edit_message_text(
            "📭 Aucune vidéo d'aide.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ Ajouter", callback_data="add_help_video"),
                InlineKeyboardButton("🔙 Retour", callback_data="help_videos_menu")
            ]])
        )
        return
    
    text = "📝 <b>Sélectionnez une vidéo à gérer :</b>\n\n"
    
    keyboard = []
    for v in videos:
        status = "✅" if v['is_active'] else "❌"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {v['title'][:30]}",
                callback_data=f"edit_help_video_{v['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="help_videos_menu")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ==================== AJOUTER UNE VIDÉO ====================

async def add_help_video_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre l'ajout d'une vidéo d'aide"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    context.user_data['adding_help_video'] = True
    context.user_data['help_video_step'] = 'waiting_video'
    
    cloud_status = "☁️ Cloudinary activé" if is_cloudinary_configured() else "⚠️ Cloudinary non configuré"
    
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="help_videos_menu")]]
    
    await query.edit_message_text(
        f"📹 <b>Ajouter une vidéo d'aide</b>\n\n"
        f"{cloud_status}\n\n"
        f"Envoyez la vidéo directement ou un lien URL :\n\n"
        f"💡 <i>Formats acceptés : MP4, liens YouTube, etc.</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_help_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère l'upload de vidéo d'aide"""
    if not context.user_data.get('adding_help_video'):
        return False
    
    if not await admin_required(update):
        return True
    
    step = context.user_data.get('help_video_step')
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="help_videos_menu")]]
    
    if step == 'waiting_video':
        # Réception d'une vidéo
        if update.message.video:
            if is_cloudinary_configured():
                loading_msg = await update.message.reply_text(
                    "☁️ <b>Upload vers le cloud...</b>\n⏳ Patientez...",
                    parse_mode="HTML"
                )
                
                result = await upload_video_from_telegram(
                    context.bot,
                    update.message.video.file_id,
                    f"help_video_{update.message.video.file_id[:10]}"
                )
                
                await loading_msg.delete()
                
                if result['success']:
                    context.user_data['help_cloud_url'] = result['url']
                    context.user_data['help_cloud_public_id'] = result['public_id']
                    context.user_data['help_duration'] = result.get('duration')
                    context.user_data['help_video_step'] = 'waiting_title'
                    
                    size_mb = round(result.get('size', 0) / 1024 / 1024, 2)
                    await update.message.reply_text(
                        f"✅ <b>Vidéo uploadée !</b>\n"
                        f"📊 Taille : {size_mb} MB\n\n"
                        f"📝 Entrez le titre de la vidéo :",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await update.message.reply_text(
                        f"❌ <b>Erreur upload :</b> {result.get('error')}\n\n"
                        f"Réessayez ou envoyez un lien URL.",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            else:
                # Sans Cloudinary, on garde le file_id
                context.user_data['help_video_file_id'] = update.message.video.file_id
                context.user_data['help_duration'] = update.message.video.duration
                context.user_data['help_video_step'] = 'waiting_title'
                
                await update.message.reply_text(
                    "✅ <b>Vidéo reçue !</b>\n\n"
                    "📝 Entrez le titre de la vidéo :",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        # Réception d'un lien
        elif update.message.text and ('http' in update.message.text.lower()):
            context.user_data['help_video_url'] = update.message.text.strip()
            context.user_data['help_video_step'] = 'waiting_title'
            
            await update.message.reply_text(
                "✅ <b>Lien enregistré !</b>\n\n"
                "📝 Entrez le titre de la vidéo :",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                "❌ Veuillez envoyer une vidéo ou un lien URL valide.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif step == 'waiting_title':
        title = update.message.text.strip()
        
        if len(title) < 3:
            await update.message.reply_text(
                "❌ Titre trop court (min 3 caractères).\nRéessayez :",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return True
        
        if len(title) > 100:
            await update.message.reply_text(
                "❌ Titre trop long (max 100 caractères).\nRéessayez :",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return True
        
        context.user_data['help_video_title'] = title
        context.user_data['help_video_step'] = 'waiting_description'
        
        keyboard.append([InlineKeyboardButton("⏭ Passer", callback_data="skip_help_description")])
        
        await update.message.reply_text(
            f"✅ Titre : <b>{title}</b>\n\n"
            f"📋 Entrez une description (optionnel) :\n\n"
            f"<i>Décrivez ce que montre cette vidéo.</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif step == 'waiting_description':
        description = update.message.text.strip()
        
        if len(description) > 500:
            await update.message.reply_text(
                "❌ Description trop longue (max 500 caractères).\nRéessayez :",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return True
        
        context.user_data['help_video_description'] = description
        
        # Créer la vidéo
        await finalize_help_video(update, context)
    
    return True


async def skip_help_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Passe l'étape de description"""
    query = update.callback_query
    await query.answer()
    
    if not context.user_data.get('adding_help_video'):
        return
    
    context.user_data['help_video_description'] = None
    
    # Créer la vidéo
    await finalize_help_video(update, context, from_callback=True)


async def finalize_help_video(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback: bool = False):
    """Finalise la création de la vidéo d'aide"""
    # Récupérer les données
    title = context.user_data.get('help_video_title', 'Vidéo d\'aide')
    description = context.user_data.get('help_video_description')
    video_url = context.user_data.get('help_video_url')
    video_file_id = context.user_data.get('help_video_file_id')
    cloud_url = context.user_data.get('help_cloud_url')
    cloud_public_id = context.user_data.get('help_cloud_public_id')
    duration = context.user_data.get('help_duration')
    
    # Calculer l'ordre d'affichage
    videos = await get_help_videos(active_only=False)
    display_order = len(videos) + 1
    
    # Créer la vidéo
    video = await create_help_video(
        title=title,
        description=description,
        video_url=video_url,
        video_file_id=video_file_id,
        cloud_url=cloud_url,
        cloud_public_id=cloud_public_id,
        duration=duration,
        display_order=display_order
    )
    
    # Nettoyer
    keys_to_remove = [k for k in context.user_data.keys() if k.startswith('help_') or k == 'adding_help_video']
    for k in keys_to_remove:
        del context.user_data[k]
    
    # Déterminer le type de stockage
    if cloud_url:
        storage = "☁️ Cloud"
    elif video_url:
        storage = "🔗 URL"
    else:
        storage = "📱 Telegram"
    
    text = (
        f"✅ <b>Vidéo d'aide créée !</b>\n\n"
        f"📹 <b>{video['title']}</b>\n"
        f"📦 Stockage : {storage}\n"
        f"📍 Position : #{video['display_order']}\n"
        f"🆔 ID : {video['id']}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Voir toutes les vidéos", callback_data="help_videos_menu")],
        [InlineKeyboardButton("➕ Ajouter une autre", callback_data="add_help_video")],
        [InlineKeyboardButton("🏠 Menu principal", callback_data="admin_menu")]
    ])
    
    if from_callback:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== MODIFIER UNE VIDÉO ====================

async def edit_help_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les options d'édition d'une vidéo"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    video_id = int(query.data.replace("edit_help_video_", ""))
    video = await get_help_video_by_id(video_id)
    
    if not video:
        await query.edit_message_text(
            "❌ Vidéo introuvable.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Retour", callback_data="help_videos_menu")
            ]])
        )
        return
    
    status = "✅ Active" if video['is_active'] else "❌ Inactive"
    storage = "☁️ Cloud" if video['cloud_url'] else ("🔗 URL" if video['video_url'] else "📱 Telegram")
    
    text = (
        f"📹 <b>{video['title']}</b>\n\n"
        f"📋 {video['description'] or 'Pas de description'}\n\n"
        f"📊 <b>Détails :</b>\n"
        f"• État : {status}\n"
        f"• Stockage : {storage}\n"
        f"• Position : #{video['display_order']}\n"
        f"• Vues : {video['views_count']}\n"
        f"• ID : {video['id']}"
    )
    
    toggle_text = "❌ Désactiver" if video['is_active'] else "✅ Activer"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Modifier titre", callback_data=f"edit_help_title_{video_id}")],
        [InlineKeyboardButton("📝 Modifier description", callback_data=f"edit_help_desc_{video_id}")],
        [
            InlineKeyboardButton("⬆️", callback_data=f"help_order_up_{video_id}"),
            InlineKeyboardButton(f"Position: {video['display_order']}", callback_data="noop"),
            InlineKeyboardButton("⬇️", callback_data=f"help_order_down_{video_id}")
        ],
        [InlineKeyboardButton(toggle_text, callback_data=f"toggle_help_video_{video_id}")],
        [InlineKeyboardButton("🗑 Supprimer", callback_data=f"delete_help_video_{video_id}")],
        [InlineKeyboardButton("🔙 Retour", callback_data="manage_help_videos")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def toggle_help_video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Active/désactive une vidéo d'aide"""
    query = update.callback_query
    
    if not await admin_required(update):
        return
    
    video_id = int(query.data.replace("toggle_help_video_", ""))
    video = await toggle_help_video(video_id)
    
    if video:
        status = "activée ✅" if video['is_active'] else "désactivée ❌"
        await query.answer(f"Vidéo {status}")
        await edit_help_video(update, context)
    else:
        await query.answer("❌ Erreur", show_alert=True)


async def help_order_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monte une vidéo dans l'ordre"""
    query = update.callback_query
    
    if not await admin_required(update):
        return
    
    video_id = int(query.data.replace("help_order_up_", ""))
    video = await get_help_video_by_id(video_id)
    
    if video and video['display_order'] > 1:
        await reorder_help_video(video_id, video['display_order'] - 1)
        await query.answer("⬆️ Monté")
    else:
        await query.answer("Déjà en haut")
    
    # Reconstruire le callback data pour edit_help_video
    query.data = f"edit_help_video_{video_id}"
    await edit_help_video(update, context)


async def help_order_down(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Descend une vidéo dans l'ordre"""
    query = update.callback_query
    
    if not await admin_required(update):
        return
    
    video_id = int(query.data.replace("help_order_down_", ""))
    video = await get_help_video_by_id(video_id)
    
    if video:
        await reorder_help_video(video_id, video['display_order'] + 1)
        await query.answer("⬇️ Descendu")
    
    query.data = f"edit_help_video_{video_id}"
    await edit_help_video(update, context)


async def delete_help_video_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demande confirmation pour supprimer"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    video_id = int(query.data.replace("delete_help_video_", ""))
    video = await get_help_video_by_id(video_id)
    
    if not video:
        await query.answer("❌ Vidéo introuvable", show_alert=True)
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Oui, supprimer", callback_data=f"confirm_delete_help_{video_id}"),
            InlineKeyboardButton("❌ Non", callback_data=f"edit_help_video_{video_id}")
        ]
    ]
    
    await query.edit_message_text(
        f"🗑 <b>Supprimer cette vidéo ?</b>\n\n"
        f"📹 {video['title']}\n\n"
        f"⚠️ Cette action est irréversible.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def confirm_delete_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirme la suppression"""
    query = update.callback_query
    
    if not await admin_required(update):
        return
    
    video_id = int(query.data.replace("confirm_delete_help_", ""))
    
    if await delete_help_video(video_id):
        await query.answer("✅ Vidéo supprimée")
        
        # Retour au menu
        query.data = "help_videos_menu"
        await help_videos_menu(update, context)
    else:
        await query.answer("❌ Erreur lors de la suppression", show_alert=True)


# ==================== MODIFIER TITRE/DESCRIPTION ====================

async def edit_help_title_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre la modification du titre"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    video_id = int(query.data.replace("edit_help_title_", ""))
    video = await get_help_video_by_id(video_id)
    
    if not video:
        await query.answer("❌ Vidéo introuvable", show_alert=True)
        return
    
    context.user_data['editing_help_video_id'] = video_id
    context.user_data['editing_help_field'] = 'title'
    
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data=f"edit_help_video_{video_id}")]]
    
    await query.edit_message_text(
        f"✏️ <b>Modifier le titre</b>\n\n"
        f"Titre actuel : <b>{video['title']}</b>\n\n"
        f"Envoyez le nouveau titre :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def edit_help_desc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre la modification de la description"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    video_id = int(query.data.replace("edit_help_desc_", ""))
    video = await get_help_video_by_id(video_id)
    
    if not video:
        await query.answer("❌ Vidéo introuvable", show_alert=True)
        return
    
    context.user_data['editing_help_video_id'] = video_id
    context.user_data['editing_help_field'] = 'description'
    
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data=f"edit_help_video_{video_id}")]]
    
    current_desc = video['description'] or "Aucune description"
    
    await query.edit_message_text(
        f"📝 <b>Modifier la description</b>\n\n"
        f"Description actuelle :\n<i>{current_desc}</i>\n\n"
        f"Envoyez la nouvelle description :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_help_video_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la modification du titre ou description"""
    video_id = context.user_data.get('editing_help_video_id')
    field = context.user_data.get('editing_help_field')
    
    if not video_id or not field:
        return False
    
    if not await admin_required(update):
        return True
    
    new_value = update.message.text.strip()
    
    # Validation
    if field == 'title':
        if len(new_value) < 3 or len(new_value) > 100:
            await update.message.reply_text(
                "❌ Le titre doit faire entre 3 et 100 caractères.\nRéessayez :"
            )
            return True
    elif field == 'description':
        if len(new_value) > 500:
            await update.message.reply_text(
                "❌ La description ne peut pas dépasser 500 caractères.\nRéessayez :"
            )
            return True
    
    # Mise à jour
    await update_help_video(video_id, **{field: new_value})
    
    # Nettoyer
    del context.user_data['editing_help_video_id']
    del context.user_data['editing_help_field']
    
    field_name = "Titre" if field == 'title' else "Description"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📹 Voir la vidéo", callback_data=f"edit_help_video_{video_id}")],
        [InlineKeyboardButton("📚 Toutes les vidéos", callback_data="help_videos_menu")]
    ])
    
    await update.message.reply_text(
        f"✅ <b>{field_name} mis à jour !</b>\n\n"
        f"Nouveau {field_name.lower()} : {new_value}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    return True


def get_help_videos_handlers():
    """Retourne les handlers pour les vidéos d'aide"""
    return [
        CallbackQueryHandler(help_videos_menu, pattern="^help_videos_menu$"),
        CallbackQueryHandler(manage_help_videos, pattern="^manage_help_videos$"),
        CallbackQueryHandler(add_help_video_start, pattern="^add_help_video$"),
        CallbackQueryHandler(skip_help_description, pattern="^skip_help_description$"),
        CallbackQueryHandler(edit_help_video, pattern="^edit_help_video_\\d+$"),
        CallbackQueryHandler(toggle_help_video_callback, pattern="^toggle_help_video_\\d+$"),
        CallbackQueryHandler(help_order_up, pattern="^help_order_up_\\d+$"),
        CallbackQueryHandler(help_order_down, pattern="^help_order_down_\\d+$"),
        CallbackQueryHandler(delete_help_video_confirm, pattern="^delete_help_video_\\d+$"),
        CallbackQueryHandler(confirm_delete_help, pattern="^confirm_delete_help_\\d+$"),
        CallbackQueryHandler(edit_help_title_start, pattern="^edit_help_title_\\d+$"),
        CallbackQueryHandler(edit_help_desc_start, pattern="^edit_help_desc_\\d+$"),
    ]