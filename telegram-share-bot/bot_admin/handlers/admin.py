"""
Handlers du bot admin
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from config.settings import ADMIN_IDS, BOT_USER_TOKEN
from database.queries import (
    get_pending_shares,
    get_share_by_id,
    approve_share,
    reject_share,
    get_pending_withdrawals,
    complete_withdrawal,
    reject_withdrawal,
    get_daily_stats,
    get_active_video,
    create_video,
    get_active_testimonials,
    get_all_users,
    get_users_count,
    get_user_by_id
)
from database.connection import db
from bot_admin.keyboards.admin_menus import (
    admin_main_menu,
    share_validation_keyboard,
    rejection_reasons_keyboard,
    withdrawal_action_keyboard,
    video_management_keyboard,
    video_duration_keyboard,
    back_to_menu_keyboard,
    broadcast_confirm_keyboard
)
from services.notifications import (
    notify_share_approved,
    notify_share_rejected,
    notify_withdrawal_completed,
    notify_withdrawal_rejected,
    notify_new_video,
    notify_referral_bonus,
    broadcast_message
)
from utils.helpers import format_amount, format_datetime


def is_admin(user_id: int) -> bool:
    """Vérifie si l'utilisateur est admin"""
    return user_id in ADMIN_IDS


async def admin_required(update: Update) -> bool:
    """Décorateur pour vérifier les droits admin"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        if update.callback_query:
            await update.callback_query.answer("❌ Accès non autorisé", show_alert=True)
        else:
            await update.message.reply_text("❌ Accès non autorisé")
        return False
    return True


# ==================== MENU PRINCIPAL ====================

async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start admin"""
    if not await admin_required(update):
        return
    
    stats = await get_daily_stats()
    
    text = f"""
🔐 <b>Panel Admin</b>

📊 <b>Aujourd'hui :</b>
• Nouveaux users : {stats['new_users_today']}
• Partages soumis : {stats['shares_today']}
• Approuvés : {stats['approved_today']}
• Payé : {format_amount(stats['paid_today'])}

⏳ <b>En attente :</b>
• Preuves : {stats['pending_shares']}
• Retraits : {stats['pending_withdrawals']} ({format_amount(stats['pending_amount'])})

👥 Total utilisateurs : {stats['total_users']}
"""
    
    await update.message.reply_text(
        text,
        reply_markup=admin_main_menu(),
        parse_mode="HTML"
    )


async def admin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retour au menu admin"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    stats = await get_daily_stats()
    
    text = f"""
🔐 <b>Panel Admin</b>

⏳ <b>En attente :</b>
• Preuves : {stats['pending_shares']}
• Retraits : {stats['pending_withdrawals']}
"""
    
    await query.edit_message_text(
        text,
        reply_markup=admin_main_menu(),
        parse_mode="HTML"
    )


# ==================== VALIDATION DES PARTAGES ====================

async def pending_shares_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les preuves en attente"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    shares = await get_pending_shares(limit=1)
    
    try:
        await query.message.delete()
    except:
        pass
    
    if not shares:
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="✅ <b>Aucune preuve en attente !</b>",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    share = shares[0]
    await show_share_for_validation(query, share, context)


async def show_share_for_validation(query, share: dict, context: ContextTypes.DEFAULT_TYPE):
    """Affiche un partage pour validation - avec support Cloudinary"""
    try:
        await query.message.delete()
    except:
        pass
    
    total = await db.fetchval("SELECT COUNT(*) FROM shares WHERE status = 'pending'")
    
    # Formatage de la date
    created_at = share.get('created_at')
    if created_at and hasattr(created_at, 'strftime'):
        date_str = created_at.strftime('%d/%m/%Y %H:%M')
    else:
        date_str = 'N/A'
    
    caption = (
        f"📋 <b>Preuve #{share['id']}</b> ({total} en attente)\n\n"
        f"👤 {share.get('first_name', 'N/A')} (@{share.get('username', 'N/A')})\n"
        f"📱 {share['platform'].upper()}\n"
        f"👥 {share['group_name']}\n"
        f"🔗 {share['group_link']}\n"
        f"📅 {date_str}"
    )
    
    # Utiliser URL Cloudinary si disponible, sinon file_id
    photo = share.get('proof_image_url') or share.get('proof_image_file_id')
    
    try:
        await context.bot.send_photo(
            chat_id=query.from_user.id,
            photo=photo,
            caption=caption,
            reply_markup=share_validation_keyboard(share['id']),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"❌ Erreur affichage preuve: {e}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"❌ Erreur image: {str(e)[:50]}\n\n{caption}",
            reply_markup=share_validation_keyboard(share['id']),
            parse_mode="HTML"
        )


async def show_next_pending(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la preuve suivante - avec support Cloudinary"""
    shares = await get_pending_shares(limit=1)
    
    if not shares:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ <b>Aucune preuve en attente !</b>",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    share = shares[0]
    total = await db.fetchval("SELECT COUNT(*) FROM shares WHERE status = 'pending'")
    
    caption = (
        f"📋 <b>Preuve #{share['id']}</b> ({total} en attente)\n\n"
        f"👤 {share.get('first_name', 'N/A')} (@{share.get('username', 'N/A')})\n"
        f"📱 {share['platform'].upper()}\n"
        f"👥 {share['group_name']}\n"
        f"🔗 {share['group_link']}"
    )
    
    # Utiliser URL Cloudinary si disponible, sinon file_id
    photo = share.get('proof_image_url') or share.get('proof_image_file_id')
    
    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            reply_markup=share_validation_keyboard(share['id']),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"❌ Erreur affichage preuve: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Erreur image: {str(e)[:50]}\n\n{caption}",
            reply_markup=share_validation_keyboard(share['id']),
            parse_mode="HTML"
        )


async def approve_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approuve un partage"""
    query = update.callback_query
    await query.answer("✅ Approuvé !")
    
    if not await admin_required(update):
        return
    
    share_id = int(query.data.replace("approve_", ""))
    admin_id = query.from_user.id
    
    result = await approve_share(share_id, admin_id)
    
    if not result:
        try:
            await query.message.delete()
        except:
            pass
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="❌ Erreur lors de l'approbation",
            reply_markup=back_to_menu_keyboard()
        )
        return
    
    # Notifier l'utilisateur
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1", result['user_id'])
    if user:
        from config.settings import REWARD_PER_SHARE
        try:
            await notify_share_approved(
                user['telegram_id'],
                REWARD_PER_SHARE,
                result['new_balance']
            )
        except Exception as e:
            print(f"❌ Erreur notification approbation: {e}")
    
    # Si bonus parrainage donné, notifier le parrain
    if result.get('referral_bonus_given') and result.get('referrer_id'):
        try:
            referrer = await get_user_by_id(result['referrer_id'])
            if referrer and user:
                from config.settings import REFERRAL_BONUS
                await notify_referral_bonus(
                    referrer['telegram_id'],
                    REFERRAL_BONUS,
                    user.get('first_name') or user.get('username') or 'Un utilisateur'
                )
        except Exception as e:
            print(f"❌ Erreur notification parrainage: {e}")
    
    # Passer au suivant
    shares = await get_pending_shares(limit=1)
    if shares:
        await show_share_for_validation(query, shares[0], context)
    else:
        try:
            await query.message.delete()
        except:
            pass
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="✅ Tous les partages ont été traités !",
            reply_markup=back_to_menu_keyboard()
        )


async def reject_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les options de rejet"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    share_id = int(query.data.replace("reject_", ""))
    context.user_data['rejecting_share_id'] = share_id
    
    keyboard = [
        [InlineKeyboardButton("📸 Capture illisible", callback_data="rr_capture_floue")],
        [InlineKeyboardButton("👥 Groupe < 200 membres", callback_data="rr_membres_insuffisants")],
        [InlineKeyboardButton("❌ Vidéo non visible", callback_data="rr_video_absente")],
        [InlineKeyboardButton("🔄 Preuve déjà utilisée", callback_data="rr_preuve_dupliquee")],
        [InlineKeyboardButton("✏️ Message personnalisé", callback_data="rr_custom")],
        [InlineKeyboardButton("🔙 Annuler", callback_data="pending_shares")]
    ]
    
    try:
        await query.message.delete()
    except:
        pass
    
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="❌ <b>REJETER LA PREUVE</b>\n\nChoisissez la raison :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def reject_reason_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la raison de rejet"""
    query = update.callback_query
    await query.answer()
    
    share_id = context.user_data.get('rejecting_share_id')
    if not share_id:
        await query.answer("❌ Session expirée", show_alert=True)
        return
    
    reason_code = query.data.replace("rr_", "")
    
    if reason_code == "custom":
        context.user_data['waiting_custom_reject'] = True
        keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="pending_shares")]]
        await query.edit_message_text(
            "✏️ <b>MESSAGE PERSONNALISÉ</b>\n\n"
            "Écrivez le message de rejet à envoyer à l'utilisateur :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return
    
    reasons = {
        "capture_floue": "📸 Capture d'écran illisible ou floue.",
        "membres_insuffisants": "👥 Le groupe n'a pas assez de membres (200+ requis).",
        "video_absente": "❌ La vidéo n'est pas visible sur la capture.",
        "preuve_dupliquee": "🔄 Cette preuve a déjà été utilisée."
    }
    
    reason = reasons.get(reason_code, "Preuve non conforme.")
    
    await do_reject(query.from_user.id, share_id, reason, context)
    context.user_data.clear()
    await show_next_pending(query.from_user.id, context)


async def do_reject(admin_id: int, share_id: int, reason: str, context: ContextTypes.DEFAULT_TYPE):
    """Effectue le rejet et notifie l'utilisateur"""
    share = await get_share_by_id(share_id)
    if not share:
        print(f"❌ Share {share_id} introuvable pour rejet")
        return
    
    await reject_share(share_id, admin_id, reason)
    print(f"✅ Share {share_id} rejeté en base")
    
    try:
        user = await get_user_by_id(share['user_id'])
        if user:
            print(f"📤 Envoi notification rejet à {user['telegram_id']}...")
            await notify_share_rejected(user['telegram_id'], reason)
            print(f"✅ Notification rejet envoyée à {user['telegram_id']}")
        else:
            print(f"❌ User {share['user_id']} introuvable")
    except Exception as e:
        print(f"❌ Erreur notification rejet: {e}")
        import traceback
        traceback.print_exc()


async def handle_custom_reject_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère le message de rejet personnalisé"""
    if not context.user_data.get('waiting_custom_reject'):
        return False
    
    if not await admin_required(update):
        return True
    
    share_id = context.user_data.get('rejecting_share_id')
    if not share_id:
        await update.message.reply_text("❌ Session expirée")
        return True
    
    reason = update.message.text.strip()
    
    if len(reason) < 10:
        await update.message.reply_text("❌ Message trop court (min 10 caractères)\nRéessayez :")
        return True
    
    await do_reject(update.effective_user.id, share_id, reason, context)
    context.user_data.clear()
    
    await update.message.reply_text(
        f"✅ <b>Preuve #{share_id} rejetée</b>\n\n📝 Message envoyé :\n{reason}\n\n📤 Utilisateur notifié",
        parse_mode="HTML"
    )
    
    import asyncio
    await asyncio.sleep(1)
    await show_next_pending(update.effective_user.id, context)
    return True


async def next_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Passe au partage suivant"""
    query = update.callback_query
    await query.answer()
    
    shares = await get_pending_shares(limit=1)
    if shares:
        await show_share_for_validation(query, shares[0], context)
    else:
        await query.edit_message_text("✅ Aucun partage en attente !", reply_markup=back_to_menu_keyboard())


# ==================== GESTION DES RETRAITS ====================

async def pending_withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les retraits en attente"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    withdrawals = await get_pending_withdrawals(limit=1)
    
    if not withdrawals:
        await query.edit_message_text("✅ Aucun retrait en attente !", reply_markup=back_to_menu_keyboard())
        return
    
    await show_withdrawal_for_processing(query, withdrawals[0])


async def show_withdrawal_for_processing(query, withdrawal: dict):
    """Affiche un retrait à traiter"""
    from config.settings import PAYMENT_METHODS
    
    method = PAYMENT_METHODS.get(withdrawal['payment_method'], {})
    method_name = method.get('name', withdrawal['payment_method'])
    method_emoji = method.get('emoji', '💳')
    
    text = f"""
💳 <b>Retrait à traiter</b>

👤 User: {withdrawal.get('first_name', 'N/A')} (@{withdrawal.get('username', 'N/A')})
💰 Montant: <b>{format_amount(withdrawal['amount'])}</b>

{method_emoji} Méthode: {method_name}
📍 Envoyé à: <code>{withdrawal['payment_details']}</code>

📅 Demandé: {format_datetime(withdrawal['created_at'])}
"""
    
    await query.edit_message_text(text, reply_markup=withdrawal_action_keyboard(withdrawal['id']), parse_mode="HTML")


async def complete_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Marque un retrait comme payé"""
    query = update.callback_query
    await query.answer("✅ Marqué comme payé !")
    
    if not await admin_required(update):
        return
    
    withdrawal_id = int(query.data.replace("complete_w_", ""))
    admin_id = query.from_user.id
    
    withdrawal = await db.fetchrow("SELECT * FROM withdrawals WHERE id = $1", withdrawal_id)
    if withdrawal:
        await complete_withdrawal(withdrawal_id, admin_id)
        
        user = await db.fetchrow("SELECT * FROM users WHERE id = $1", withdrawal['user_id'])
        if user:
            from config.settings import PAYMENT_METHODS
            method = PAYMENT_METHODS.get(withdrawal['payment_method'], {})
            await notify_withdrawal_completed(
                user['telegram_id'],
                withdrawal['amount'],
                method.get('name', withdrawal['payment_method']),
                withdrawal['payment_details']
            )
    
    withdrawals = await get_pending_withdrawals(limit=1)
    if withdrawals:
        await show_withdrawal_for_processing(query, withdrawals[0])
    else:
        await query.edit_message_text("✅ Tous les retraits ont été traités !", reply_markup=back_to_menu_keyboard())


async def reject_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rejette un retrait"""
    query = update.callback_query
    await query.answer("❌ Rejeté et remboursé")
    
    if not await admin_required(update):
        return
    
    withdrawal_id = int(query.data.replace("reject_w_", ""))
    admin_id = query.from_user.id
    
    withdrawal = await db.fetchrow("SELECT * FROM withdrawals WHERE id = $1", withdrawal_id)
    if withdrawal:
        await reject_withdrawal(withdrawal_id, admin_id, "Informations de paiement invalides")
        
        user = await db.fetchrow("SELECT * FROM users WHERE id = $1", withdrawal['user_id'])
        if user:
            await notify_withdrawal_rejected(user['telegram_id'], withdrawal['amount'], "Informations de paiement invalides")
    
    withdrawals = await get_pending_withdrawals(limit=1)
    if withdrawals:
        await show_withdrawal_for_processing(query, withdrawals[0])
    else:
        await query.edit_message_text("✅ Tous les retraits ont été traités !", reply_markup=back_to_menu_keyboard())


# ==================== GESTION DES VIDÉOS ====================

async def manage_videos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu gestion des vidéos"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    from bot_admin.handlers.videos import show_videos_list
    await show_videos_list(update, context, 0)


async def add_video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre l'ajout de vidéo"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    from services.cloud_storage import is_cloudinary_configured
    
    context.user_data['adding_video'] = True
    context.user_data['video_step'] = 'waiting_video'
    
    cloud_note = "☁️ <b>Cloudinary activé</b>\n\n" if is_cloudinary_configured() else "⚠️ <b>Cloudinary non configuré</b>\n\n"
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="admin_menu")]]
    
    await query.edit_message_text(
        f"📹 <b>Ajouter une vidéo</b>\n\n{cloud_note}Envoyez la vidéo ou un lien URL :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère l'upload de vidéo"""
    if not context.user_data.get('adding_video'):
        return
    
    if not await admin_required(update):
        return
    
    from services.cloud_storage import upload_video_from_telegram, is_cloudinary_configured
    
    step = context.user_data.get('video_step')
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="admin_menu")]]
    
    if step == 'waiting_video':
        if update.message.video:
            if is_cloudinary_configured():
                await update.message.reply_text("☁️ <b>Upload vers le cloud...</b>", parse_mode="HTML")
                
                result = await upload_video_from_telegram(context.bot, update.message.video.file_id, f"video_{update.message.video.file_id[:10]}")
                
                if result['success']:
                    context.user_data['cloud_url'] = result['url']
                    context.user_data['cloud_public_id'] = result['public_id']
                    context.user_data['duration'] = result.get('duration')
                    context.user_data['width'] = result.get('width')
                    context.user_data['height'] = result.get('height')
                    context.user_data['file_size'] = result.get('size')
                    context.user_data['video_step'] = 'waiting_title'
                    
                    size_mb = round(result.get('size', 0) / 1024 / 1024, 2)
                    await update.message.reply_text(f"✅ <b>Vidéo uploadée !</b>\n📊 {size_mb} MB\n\n📝 Entrez le titre :", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
                else:
                    await update.message.reply_text(f"❌ <b>Erreur:</b> {result.get('error')}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text("⚠️ Cloudinary non configuré. Envoyez un lien URL.", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif update.message.text and 'http' in update.message.text:
            context.user_data['video_url'] = update.message.text.strip()
            context.user_data['video_step'] = 'waiting_title'
            await update.message.reply_text("✅ Lien enregistré !\n\n📝 Entrez le titre :", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("❌ Envoyez une vidéo ou un lien valide", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif step == 'waiting_title':
        title = update.message.text.strip()
        if len(title) < 3:
            await update.message.reply_text("❌ Titre trop court (min 3 car.)")
            return
        context.user_data['video_title'] = title
        context.user_data['video_step'] = 'waiting_caption'
        await update.message.reply_text(f"✅ Titre : {title}\n\n📋 Entrez la légende :", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif step == 'waiting_caption':
        caption = update.message.text.strip()
        if len(caption) < 10:
            await update.message.reply_text("❌ Légende trop courte (min 10 car.)")
            return
        context.user_data['video_caption'] = caption
        context.user_data['video_step'] = 'waiting_duration'
        await update.message.reply_text("✅ Légende enregistrée !\n\n⏱️ Durée de validité :", reply_markup=video_duration_keyboard())


async def video_duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finalise la création de vidéo"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    hours = int(query.data.replace("duration_", ""))
    cloud_url = context.user_data.get('cloud_url')
    url = context.user_data.get('video_url')
    
    if not (cloud_url or url):
        await query.edit_message_text("❌ Aucune vidéo. Recommencez.", reply_markup=back_to_menu_keyboard())
        context.user_data.clear()
        return
    
    video = await create_video(
        title=context.user_data.get('video_title', 'Vidéo'),
        caption=context.user_data.get('video_caption', ''),
        cloud_url=cloud_url,
        cloud_public_id=context.user_data.get('cloud_public_id'),
        url=url,
        validity_hours=hours,
        file_size=context.user_data.get('file_size'),
        duration=context.user_data.get('duration'),
        width=context.user_data.get('width'),
        height=context.user_data.get('height')
    )
    
    context.user_data.clear()
    storage = "☁️ Cloud" if video.get('cloud_url') else "🔗 URL"
    
    await query.edit_message_text(
        f"✅ <b>Vidéo créée !</b>\n\n📹 {video['title']}\n📦 {storage}\n⏱️ {hours}h\n🆔 #{video['id']}",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )


# ==================== STATISTIQUES ====================

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les statistiques"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    stats = await get_daily_stats()
    
    text = f"""
📊 <b>Statistiques détaillées</b>

<b>👥 Utilisateurs</b>
• Total : {stats['total_users']}
• Nouveaux aujourd'hui : {stats['new_users_today']}

<b>📤 Partages</b>
• Aujourd'hui : {stats['shares_today']}
• Approuvés : {stats['approved_today']}
• En attente : {stats['pending_shares']}

<b>💰 Finances</b>
• Payé aujourd'hui : {format_amount(stats['paid_today'])}
• En attente : {format_amount(stats['pending_amount'])}
"""
    
    await query.edit_message_text(text, reply_markup=back_to_menu_keyboard(), parse_mode="HTML")


# ==================== BROADCAST ====================

async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre un broadcast"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    context.user_data['broadcasting'] = True
    await query.edit_message_text("📢 <b>Broadcast</b>\n\nEnvoyez le message à diffuser :", reply_markup=back_to_menu_keyboard(), parse_mode="HTML")


async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère le message de broadcast"""
    if not context.user_data.get('broadcasting'):
        return
    
    if not await admin_required(update):
        return
    
    context.user_data['broadcast_text'] = update.message.text
    users_count = await get_users_count()
    
    await update.message.reply_text(
        f"📢 <b>Confirmer l'envoi ?</b>\n\nMessage :\n{update.message.text}\n\n👥 Destinataires : {users_count}",
        reply_markup=broadcast_confirm_keyboard(),
        parse_mode="HTML"
    )


async def confirm_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirme et envoie le broadcast"""
    query = update.callback_query
    await query.answer("📤 Envoi en cours...")
    
    if not await admin_required(update):
        return
    
    message = context.user_data.get('broadcast_text', '')
    users = await db.fetch("SELECT telegram_id FROM users WHERE is_blocked = FALSE")
    user_ids = [u['telegram_id'] for u in users]
    
    await query.edit_message_text("📤 Envoi en cours...")
    result = await broadcast_message(user_ids, message)
    context.user_data.clear()
    
    await query.edit_message_text(
        f"✅ <b>Broadcast terminé !</b>\n\n📤 Envoyés : {result['success']}\n❌ Échecs : {result['failed']}",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )


# ==================== TÉMOIGNAGES ====================

async def manage_testimonials_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les témoignages"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    testimonials = await get_active_testimonials()
    text = "💬 <b>Gestion des témoignages</b>\n\n"
    
    if testimonials:
        for i, t in enumerate(testimonials, 1):
            preview = t['message'][:50] + "..." if len(t['message']) > 50 else t['message']
            status = "✅" if t['is_active'] else "❌"
            text += f"{i}. {status} {preview}\n   📊 Utilisé {t['usage_count']} fois\n\n"
    else:
        text += "Aucun témoignage configuré.\n\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Ajouter un témoignage", callback_data="add_testimonial")],
        [InlineKeyboardButton("🏠 Menu", callback_data="admin_menu")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def add_testimonial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre l'ajout d'un témoignage"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    context.user_data['adding_testimonial'] = True
    await query.edit_message_text(
        "💬 <b>Ajouter un témoignage</b>\n\nEnvoyez le message témoignage.\n\n💡 Utilisez <code>{link}</code> pour le lien du bot.",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )


async def handle_new_testimonial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère l'ajout d'un nouveau témoignage"""
    if not context.user_data.get('adding_testimonial'):
        return False
    
    if not await admin_required(update):
        return True
    
    from database.queries import create_testimonial
    
    message = update.message.text
    await create_testimonial(message)
    context.user_data.clear()
    
    await update.message.reply_text(f"✅ <b>Témoignage ajouté !</b>\n\nMessage : {message}", reply_markup=back_to_menu_keyboard(), parse_mode="HTML")
    return True


# ==================== UTILISATEURS ====================

async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Liste des utilisateurs"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    page = context.user_data.get('users_page', 0)
    limit = 10
    offset = page * limit
    
    users = await get_all_users(limit=limit, offset=offset)
    total = await get_users_count()
    
    text = f"👥 <b>Utilisateurs</b> ({total} total)\n📄 Page {page + 1}\n\n"
    
    for u in users:
        status = "🔒" if u['is_blocked'] else "✅"
        text += f"{status} <b>{u['first_name'] or 'N/A'}</b> (@{u['username'] or 'N/A'})\n"
        text += f"   💰 {u['balance']} FCFA | Total: {u['total_earned']} FCFA\n"
        text += f"   🆔 <code>{u['telegram_id']}</code>\n\n"
    
    keyboard = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"users_page_{page-1}"))
    if len(users) == limit:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"users_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("🔍 Rechercher", callback_data="search_user")])
    keyboard.append([InlineKeyboardButton("🏠 Menu", callback_data="admin_menu")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def users_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change de page"""
    query = update.callback_query
    await query.answer()
    page = int(query.data.replace("users_page_", ""))
    context.user_data['users_page'] = page
    await users_callback(update, context)


async def search_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recherche utilisateur"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    context.user_data['searching_user'] = True
    await query.edit_message_text("🔍 <b>Rechercher</b>\n\nEnvoyez le nom, @username ou ID :", reply_markup=back_to_menu_keyboard(), parse_mode="HTML")


async def handle_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la recherche"""
    if not context.user_data.get('searching_user'):
        return False
    
    if not await admin_required(update):
        return True
    
    search = update.message.text.strip()
    user = None
    
    if search.isdigit():
        user = await db.fetchrow("SELECT * FROM users WHERE telegram_id = $1", int(search))
    
    if not user and search.startswith("@"):
        user = await db.fetchrow("SELECT * FROM users WHERE username ILIKE $1", search[1:])
    
    if not user:
        user = await db.fetchrow("SELECT * FROM users WHERE first_name ILIKE $1 OR username ILIKE $1", f"%{search}%")
    
    context.user_data.clear()
    
    if not user:
        await update.message.reply_text("❌ Utilisateur non trouvé.", reply_markup=back_to_menu_keyboard())
        return True
    
    status = "🔒 Bloqué" if user['is_blocked'] else "✅ Actif"
    text = f"""
👤 <b>Détails utilisateur</b>

{status}
📛 Nom : {user['first_name'] or 'N/A'}
👤 Username : @{user['username'] or 'N/A'}
🆔 ID : <code>{user['telegram_id']}</code>

💰 Solde : <b>{user['balance']} FCFA</b>
💵 Total gagné : {user['total_earned']} FCFA
🎫 Code : <code>{user['referral_code']}</code>

📅 Inscrit : {format_datetime(user['created_at'])}
"""
    
    block_text = "🔓 Débloquer" if user['is_blocked'] else "🔒 Bloquer"
    block_action = "unblock" if user['is_blocked'] else "block"
    
    keyboard = [
        [InlineKeyboardButton(block_text, callback_data=f"{block_action}_user_{user['id']}")],
        [InlineKeyboardButton("📊 Historique", callback_data=f"user_history_{user['id']}")],
        [InlineKeyboardButton("🔙 Retour", callback_data="users")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return True


async def block_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bloque un utilisateur"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    user_id = int(query.data.replace("block_user_", ""))
    await db.execute("UPDATE users SET is_blocked = TRUE WHERE id = $1", user_id)
    await query.edit_message_text("✅ Utilisateur bloqué !", reply_markup=back_to_menu_keyboard())


async def unblock_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Débloque un utilisateur"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    user_id = int(query.data.replace("unblock_user_", ""))
    await db.execute("UPDATE users SET is_blocked = FALSE WHERE id = $1", user_id)
    await query.edit_message_text("✅ Utilisateur débloqué !", reply_markup=back_to_menu_keyboard())


async def user_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Historique utilisateur"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    user_id = int(query.data.replace("user_history_", ""))
    
    shares = await db.fetch("SELECT * FROM shares WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5", user_id)
    withdrawals = await db.fetch("SELECT * FROM withdrawals WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5", user_id)
    
    text = "📊 <b>Historique</b>\n\n<b>📤 Partages :</b>\n"
    for s in shares:
        emoji = "✅" if s['status'] == 'approved' else "❌" if s['status'] == 'rejected' else "⏳"
        text += f"{emoji} {s['group_name'][:20]} - {s['platform']}\n"
    if not shares:
        text += "Aucun\n"
    
    text += "\n<b>💳 Retraits :</b>\n"
    for w in withdrawals:
        emoji = "✅" if w['status'] == 'completed' else "❌" if w['status'] == 'rejected' else "⏳"
        text += f"{emoji} {w['amount']} FCFA - {w['payment_method']}\n"
    if not withdrawals:
        text += "Aucun\n"
    
    await query.edit_message_text(text, reply_markup=back_to_menu_keyboard(), parse_mode="HTML")


# ==================== CONFIGURATION ====================

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paramètres"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    from config.settings import REWARD_PER_SHARE, REFERRAL_BONUS, MIN_WITHDRAWAL, MAX_TELEGRAM_SHARES_PER_DAY, MAX_WHATSAPP_SHARES_PER_DAY, MIN_TELEGRAM_MEMBERS, MIN_WHATSAPP_MEMBERS, DAILY_BUDGET_LIMIT, MONTHLY_BUDGET_LIMIT, BOT_CHANNEL_LINK
    from database.queries import get_budget_used_today
    budget_today = await get_budget_used_today()
    
    text = f"""
⚙️ <b>Configuration</b>

💰 <b>Économie</b>
• Récompense : {REWARD_PER_SHARE} FCFA
• Bonus parrainage : {REFERRAL_BONUS} FCFA
• Min retrait : {MIN_WITHDRAWAL} FCFA

📊 <b>Limites</b>
• Max Telegram/jour : {MAX_TELEGRAM_SHARES_PER_DAY}
• Max WhatsApp/jour : {MAX_WHATSAPP_SHARES_PER_DAY}
• Min membres TG : {MIN_TELEGRAM_MEMBERS}
• Min membres WA : {MIN_WHATSAPP_MEMBERS}

💵 <b>Budget</b>
• Limite/jour : {format_amount(DAILY_BUDGET_LIMIT)}
• Utilisé : {format_amount(budget_today)}
• Limite/mois : {format_amount(MONTHLY_BUDGET_LIMIT)}

🔗 {BOT_CHANNEL_LINK}
"""
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Vider blacklist", callback_data="clear_blacklist")],
        [InlineKeyboardButton("🏠 Menu", callback_data="admin_menu")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def clear_blacklist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vide la blacklist"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_required(update):
        return
    
    await db.execute("DELETE FROM blacklisted_groups")
    await query.edit_message_text("✅ Blacklist vidée !", reply_markup=back_to_menu_keyboard())


def get_admin_handlers():
    """Retourne tous les handlers admin"""
    return [
        CommandHandler("start", start_admin),
        CommandHandler("pending", pending_shares_callback),
        CommandHandler("stats", stats_callback),
        CallbackQueryHandler(admin_menu_callback, pattern="^admin_menu$"),
        CallbackQueryHandler(pending_shares_callback, pattern="^pending_shares$"),
        CallbackQueryHandler(approve_share_callback, pattern="^approve_"),
        CallbackQueryHandler(reject_share_callback, pattern="^reject_\\d+$"),
        CallbackQueryHandler(reject_reason_callback, pattern="^rr_"),
        CallbackQueryHandler(next_share_callback, pattern="^next_share$"),
        CallbackQueryHandler(pending_withdrawals_callback, pattern="^pending_withdrawals$"),
        CallbackQueryHandler(complete_withdrawal_callback, pattern="^complete_w_"),
        CallbackQueryHandler(reject_withdrawal_callback, pattern="^reject_w_"),
        CallbackQueryHandler(manage_videos_callback, pattern="^manage_videos$"),
        CallbackQueryHandler(add_video_callback, pattern="^add_video$"),
        CallbackQueryHandler(video_duration_callback, pattern="^duration_"),
        CallbackQueryHandler(manage_testimonials_callback, pattern="^manage_testimonials$"),
        CallbackQueryHandler(add_testimonial_callback, pattern="^add_testimonial$"),
        CallbackQueryHandler(users_callback, pattern="^users$"),
        CallbackQueryHandler(users_page_callback, pattern="^users_page_"),
        CallbackQueryHandler(search_user_callback, pattern="^search_user$"),
        CallbackQueryHandler(block_user_callback, pattern="^block_user_"),
        CallbackQueryHandler(unblock_user_callback, pattern="^unblock_user_"),
        CallbackQueryHandler(user_history_callback, pattern="^user_history_"),
        CallbackQueryHandler(settings_callback, pattern="^settings$"),
        CallbackQueryHandler(clear_blacklist_callback, pattern="^clear_blacklist$"),
        CallbackQueryHandler(stats_callback, pattern="^stats$"),
        CallbackQueryHandler(broadcast_callback, pattern="^broadcast$"),
        CallbackQueryHandler(confirm_broadcast_callback, pattern="^confirm_broadcast$"),
    ]
