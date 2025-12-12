"""
Gestion des vidéos par l'admin - Version Expert avec Cloudinary
"""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from database.queries import (
    get_active_video,
    get_video_by_id,
    get_all_videos,
    get_videos_count,
    create_video,
    delete_video,
    toggle_video_active,
    extend_video_validity
)
from services.cloud_storage import upload_video_from_telegram, delete_from_cloudinary, is_cloudinary_configured
from config.settings import ADMIN_IDS


async def videos_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal des vidéos"""
    query = update.callback_query
    if query:
        await query.answer()
    
    await show_videos_list(update, context, 0)


async def show_videos_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    """Affiche la liste des vidéos"""
    limit = 5
    offset = page * limit
    
    videos = await get_all_videos(limit=limit, offset=offset)
    total = await get_videos_count()
    active = await get_active_video()
    
    # Vérifier si Cloudinary est configuré
    cloud_status = "✅ Cloudinary configuré" if is_cloudinary_configured() else "⚠️ Cloudinary non configuré"
    
    text = f"🎬 <b>GESTION DES VIDÉOS</b>\n\n"
    text += f"☁️ {cloud_status}\n\n"
    
    if active:
        remaining = active['expires_at'] - datetime.now()
        hours = max(0, int(remaining.total_seconds() // 3600))
        text += f"✅ <b>Active :</b> {active['title']}\n"
        text += f"⏱️ Expire dans : {hours}h\n\n"
    else:
        text += "⚠️ <b>Aucune vidéo active !</b>\n\n"
    
    text += f"📊 Total : {total} vidéo(s) | Page {page + 1}\n\n"
    
    keyboard = []
    
    if videos:
        for v in videos:
            is_active = v['is_active'] and v['expires_at'] > datetime.now()
            status = "✅" if is_active else "❌"
            source = "☁️" if v.get('cloud_url') else "🔗" if v.get('url') else "⚠️"
            
            title_short = v['title'][:18] + "..." if len(v['title']) > 18 else v['title']
            text += f"{status}{source} <b>{title_short}</b> (#{v['id']})\n"
            
            keyboard.append([
                InlineKeyboardButton(f"👁️ #{v['id']}", callback_data=f"vid_view_{v['id']}"),
                InlineKeyboardButton("🗑️", callback_data=f"vid_confirm_{v['id']}")
            ])
    else:
        text += "📭 Aucune vidéo enregistrée.\n"
    
    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Préc", callback_data=f"vid_page_{page-1}"))
    if len(videos) == limit:
        nav.append(InlineKeyboardButton("Suiv ➡️", callback_data=f"vid_page_{page+1}"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("➕ Ajouter une vidéo", callback_data="vid_add")])
    keyboard.append([InlineKeyboardButton("🔙 Menu principal", callback_data="admin_menu")])
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            await update.callback_query.message.reply_text(
                text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def vid_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change de page"""
    query = update.callback_query
    await query.answer()
    page = int(query.data.replace("vid_page_", ""))
    await show_videos_list(update, context, page)


async def vid_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les détails d'une vidéo"""
    query = update.callback_query
    await query.answer()
    
    video_id = int(query.data.replace("vid_view_", ""))
    video = await get_video_by_id(video_id)
    
    if not video:
        await query.answer("❌ Vidéo introuvable", show_alert=True)
        return
    
    is_active = video['is_active'] and video['expires_at'] > datetime.now()
    status = "✅ Active" if is_active else "❌ Inactive"
    expired = " (EXPIRÉE)" if video['expires_at'] < datetime.now() else ""
    
    remaining = video['expires_at'] - datetime.now()
    hours = max(0, int(remaining.total_seconds() // 3600))
    
    size_mb = f"{round(video['file_size']/1024/1024, 2)} MB" if video.get('file_size') else "N/A"
    storage = "☁️ Cloudinary" if video.get('cloud_url') else "🔗 URL externe" if video.get('url') else "⚠️ Aucun"
    
    text = f"""
🎬 <b>VIDÉO #{video['id']}</b>

📝 <b>Titre :</b> {video['title']}
{status}{expired}

📋 <b>Légende :</b>
<i>{video['caption'][:200]}{'...' if len(video['caption']) > 200 else ''}</i>

📊 <b>Informations :</b>
• Stockage : {storage}
• Durée : {video.get('duration', 'N/A')}s
• Taille : {size_mb}
• Résolution : {video.get('width', '?')}x{video.get('height', '?')}
• Expire dans : {hours}h

📅 Créé le : {video['created_at'].strftime('%d/%m/%Y %H:%M')}
"""
    
    toggle_text = "❌ Désactiver" if video['is_active'] else "✅ Activer"
    
    keyboard = [
        [InlineKeyboardButton("📤 Tester l'envoi", callback_data=f"vid_test_{video['id']}")],
        [InlineKeyboardButton(toggle_text, callback_data=f"vid_toggle_{video['id']}")],
        [
            InlineKeyboardButton("+24h", callback_data=f"vid_ext_{video['id']}_24"),
            InlineKeyboardButton("+48h", callback_data=f"vid_ext_{video['id']}_48"),
            InlineKeyboardButton("+72h", callback_data=f"vid_ext_{video['id']}_72")
        ],
        [InlineKeyboardButton("🗑️ Supprimer", callback_data=f"vid_confirm_{video['id']}")],
        [InlineKeyboardButton("🔙 Retour", callback_data="vid_list")]
    ]
    
    await query.edit_message_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def vid_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Teste l'envoi de la vidéo"""
    query = update.callback_query
    
    video_id = int(query.data.replace("vid_test_", ""))
    video = await get_video_by_id(video_id)
    
    if not video:
        await query.answer("❌ Vidéo introuvable", show_alert=True)
        return
    
    await query.answer("📤 Envoi en cours...")
    
    try:
        video_url = video.get('cloud_url') or video.get('url')
        
        if video_url:
            await context.bot.send_video(
                chat_id=query.from_user.id,
                video=video_url,
                caption=f"🧪 <b>TEST</b> - {video['title']}\n\n{video['caption'][:500]}",
                parse_mode="HTML"
            )
            await query.answer("✅ Vidéo envoyée avec succès !", show_alert=True)
        else:
            await query.answer("❌ Aucune URL de vidéo", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Erreur: {str(e)[:50]}", show_alert=True)


async def vid_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Active/désactive une vidéo"""
    query = update.callback_query
    
    video_id = int(query.data.replace("vid_toggle_", ""))
    video = await toggle_video_active(video_id)
    
    if video:
        status = "activée ✅" if video['is_active'] else "désactivée ❌"
        await query.answer(f"Vidéo {status}", show_alert=True)
    
    query.data = f"vid_view_{video_id}"
    await vid_view_callback(update, context)


async def vid_ext_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prolonge la validité"""
    query = update.callback_query
    
    parts = query.data.replace("vid_ext_", "").split("_")
    video_id = int(parts[0])
    hours = int(parts[1])
    
    await extend_video_validity(video_id, hours)
    await query.answer(f"✅ Prolongé de {hours}h", show_alert=True)
    
    query.data = f"vid_view_{video_id}"
    await vid_view_callback(update, context)


async def vid_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirme la suppression"""
    query = update.callback_query
    await query.answer()
    
    video_id = int(query.data.replace("vid_confirm_", ""))
    video = await get_video_by_id(video_id)
    
    if not video:
        await query.answer("❌ Vidéo introuvable", show_alert=True)
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Oui, supprimer", callback_data=f"vid_del_{video_id}"),
            InlineKeyboardButton("❌ Annuler", callback_data=f"vid_view_{video_id}")
        ]
    ]
    
    await query.edit_message_text(
        f"⚠️ <b>CONFIRMER LA SUPPRESSION</b>\n\n"
        f"Vidéo : <b>{video['title']}</b>\n\n"
        f"Cette action supprimera également le fichier du cloud.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def vid_del_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Supprime la vidéo"""
    query = update.callback_query
    
    video_id = int(query.data.replace("vid_del_", ""))
    video = await get_video_by_id(video_id)
    
    # Supprimer de Cloudinary si nécessaire
    if video and video.get('cloud_public_id'):
        await delete_from_cloudinary(video['cloud_public_id'])
    
    await delete_video(video_id)
    await query.answer("🗑️ Vidéo supprimée", show_alert=True)
    
    await show_videos_list(update, context, 0)


async def vid_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre l'ajout de vidéo"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.clear()
    context.user_data['adding_video'] = True
    context.user_data['video_step'] = 'waiting_video'
    
    cloud_note = ""
    if is_cloudinary_configured():
        cloud_note = "☁️ <b>Cloudinary activé</b> - Les vidéos seront stockées dans le cloud.\n\n"
    else:
        cloud_note = "⚠️ <b>Cloudinary non configuré</b> - Utilisez des liens directs.\n\n"
    
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="vid_cancel")]]
    
    await query.edit_message_text(
        f"🎬 <b>AJOUTER UNE VIDÉO</b>\n\n"
        f"{cloud_note}"
        f"📹 <b>Étape 1/4</b> - Envoyez la vidéo\n\n"
        f"• Envoyez un fichier vidéo (MP4, MOV - max 50MB)\n"
        f"• Ou envoyez un lien direct vers la vidéo",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def vid_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annule l'ajout"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🔙 Retour aux vidéos", callback_data="vid_list")]]
    await query.edit_message_text(
        "❌ Ajout de vidéo annulé.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def vid_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retourne à la liste"""
    query = update.callback_query
    await query.answer()
    await show_videos_list(update, context, 0)


async def vid_dur_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finalise la création de la vidéo"""
    query = update.callback_query
    await query.answer("⏳ Création en cours...")
    
    if not context.user_data.get('adding_video'):
        await query.edit_message_text("❌ Session expirée. Recommencez.")
        return
    
    hours = int(query.data.replace("vid_dur_", ""))
    
    cloud_url = context.user_data.get('cloud_url')
    cloud_public_id = context.user_data.get('cloud_public_id')
    url = context.user_data.get('video_url')
    title = context.user_data.get('video_title')
    caption = context.user_data.get('video_caption')
    
    if not (cloud_url or url):
        await query.edit_message_text("❌ Aucune vidéo. Recommencez.")
        context.user_data.clear()
        return
    
    if not title or not caption:
        await query.edit_message_text("❌ Titre/légende manquant. Recommencez.")
        context.user_data.clear()
        return
    
    video = await create_video(
        title=title,
        caption=caption,
        cloud_url=cloud_url,
        cloud_public_id=cloud_public_id,
        url=url,
        validity_hours=hours,
        file_size=context.user_data.get('file_size'),
        duration=context.user_data.get('duration'),
        width=context.user_data.get('width'),
        height=context.user_data.get('height')
    )
    
    context.user_data.clear()
    
    storage = "☁️ Cloudinary" if video.get('cloud_url') else "🔗 URL"
    
    keyboard = [
        [InlineKeyboardButton("📤 Tester l'envoi", callback_data=f"vid_test_{video['id']}")],
        [InlineKeyboardButton("📋 Liste des vidéos", callback_data="vid_list")]
    ]
    
    await query.edit_message_text(
        f"✅ <b>VIDÉO CRÉÉE AVEC SUCCÈS !</b>\n\n"
        f"📝 <b>Titre :</b> {video['title']}\n"
        f"📦 <b>Stockage :</b> {storage}\n"
        f"⏱️ <b>Validité :</b> {hours}h\n"
        f"🆔 <b>ID :</b> #{video['id']}\n\n"
        f"🎉 La vidéo est maintenant active !",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère l'upload de vidéo par l'admin"""
    if not context.user_data.get('adding_video'):
        return
    
    step = context.user_data.get('video_step')
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="vid_cancel")]]
    
    # Étape 1: Réception vidéo
    if step == 'waiting_video':
        if update.message.video:
            # Upload vers Cloudinary si configuré
            if is_cloudinary_configured():
                await update.message.reply_text(
                    "☁️ <b>Upload vers le cloud en cours...</b>\n\n"
                    "⏳ Veuillez patienter...",
                    parse_mode="HTML"
                )
                
                result = await upload_video_from_telegram(
                    context.bot,
                    update.message.video.file_id,
                    f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                
                if result['success']:
                    context.user_data['cloud_url'] = result['url']
                    context.user_data['cloud_public_id'] = result['public_id']
                    context.user_data['duration'] = result.get('duration')
                    context.user_data['width'] = result.get('width')
                    context.user_data['height'] = result.get('height')
                    context.user_data['file_size'] = result.get('size')
                    context.user_data['video_step'] = 'waiting_title'
                    
                    size_mb = round(result.get('size', 0) / 1024 / 1024, 2)
                    
                    await update.message.reply_text(
                        f"✅ <b>Vidéo uploadée sur le cloud !</b>\n\n"
                        f"📊 {size_mb} MB | {result.get('duration', 'N/A')}s\n\n"
                        f"📝 <b>Étape 2/4</b> - Entrez le titre :",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await update.message.reply_text(
                        f"❌ <b>Erreur d'upload :</b> {result.get('error', 'Inconnue')}\n\n"
                        f"Réessayez ou envoyez un lien direct.",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            else:
                # Sans Cloudinary, demander un lien
                await update.message.reply_text(
                    "⚠️ <b>Cloudinary non configuré</b>\n\n"
                    "Veuillez envoyer un lien direct vers la vidéo (URL).\n\n"
                    "Pour activer l'upload de fichiers, configurez Cloudinary dans .env",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            return
        
        elif update.message.text and ('http' in update.message.text):
            context.user_data['video_url'] = update.message.text.strip()
            context.user_data['video_step'] = 'waiting_title'
            
            await update.message.reply_text(
                "✅ <b>Lien enregistré !</b>\n\n"
                "📝 <b>Étape 2/4</b> - Entrez le titre :",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        else:
            await update.message.reply_text(
                "❌ Envoyez une vidéo ou un lien valide.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    
    # Étape 2: Titre
    elif step == 'waiting_title':
        if update.message.text:
            title = update.message.text.strip()
            if len(title) < 3:
                await update.message.reply_text("❌ Titre trop court (min 3 caractères)")
                return
            
            context.user_data['video_title'] = title
            context.user_data['video_step'] = 'waiting_caption'
            
            await update.message.reply_text(
                f"✅ <b>Titre :</b> {title}\n\n"
                f"📋 <b>Étape 3/4</b> - Entrez la légende/description :",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    
    # Étape 3: Légende
    elif step == 'waiting_caption':
        if update.message.text:
            caption = update.message.text.strip()
            if len(caption) < 10:
                await update.message.reply_text("❌ Légende trop courte (min 10 caractères)")
                return
            
            context.user_data['video_caption'] = caption
            context.user_data['video_step'] = 'waiting_duration'
            
            dur_keyboard = [
                [
                    InlineKeyboardButton("24h", callback_data="vid_dur_24"),
                    InlineKeyboardButton("48h", callback_data="vid_dur_48")
                ],
                [
                    InlineKeyboardButton("72h", callback_data="vid_dur_72"),
                    InlineKeyboardButton("1 semaine", callback_data="vid_dur_168")
                ],
                [InlineKeyboardButton("❌ Annuler", callback_data="vid_cancel")]
            ]
            
            await update.message.reply_text(
                "✅ <b>Légende enregistrée !</b>\n\n"
                "⏱️ <b>Étape 4/4</b> - Durée de validité :",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(dur_keyboard)
            )
            return


def get_video_admin_handlers():
    """Retourne les handlers admin pour les vidéos"""
    return [
        CallbackQueryHandler(videos_menu, pattern="^manage_videos$"),
        CallbackQueryHandler(vid_list_callback, pattern="^vid_list$"),
        CallbackQueryHandler(vid_page_callback, pattern=r"^vid_page_\d+$"),
        CallbackQueryHandler(vid_view_callback, pattern=r"^vid_view_\d+$"),
        CallbackQueryHandler(vid_test_callback, pattern=r"^vid_test_\d+$"),
        CallbackQueryHandler(vid_toggle_callback, pattern=r"^vid_toggle_\d+$"),
        CallbackQueryHandler(vid_ext_callback, pattern=r"^vid_ext_\d+_\d+$"),
        CallbackQueryHandler(vid_confirm_callback, pattern=r"^vid_confirm_\d+$"),
        CallbackQueryHandler(vid_del_callback, pattern=r"^vid_del_\d+$"),
        CallbackQueryHandler(vid_add_callback, pattern="^vid_add$"),
        CallbackQueryHandler(vid_cancel_callback, pattern="^vid_cancel$"),
        CallbackQueryHandler(vid_dur_callback, pattern=r"^vid_dur_\d+$"),
    ]
