"""
User management handlers for admin bot
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import queries
from bot_admin.keyboards import admin_menus
from bot_admin.handlers.auth import is_authorized
from utils.helpers import format_currency, format_datetime, get_status_emoji


# Conversation states
SEARCH_USER = 1


async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user management menu"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    stats = await queries.get_global_stats()
    
    await query.message.edit_text(
        f"👥 <b>Gestion des Utilisateurs</b>\n\n"
        f"📊 Total : {stats.get('total_users', 0)} utilisateurs\n"
        f"🆕 Nouveaux aujourd'hui : {stats.get('new_users_today', 0)}\n\n"
        f"🔍 Envoyez le <b>@username</b> ou <b>Telegram ID</b> pour rechercher un utilisateur :",
        reply_markup=admin_menus.back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    
    return SEARCH_USER


async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for a user"""
    if not await is_authorized(update):
        return ConversationHandler.END
    
    search_term = update.message.text.strip()
    
    user = None
    
    # Try to find by Telegram ID
    if search_term.isdigit():
        user = await queries.get_user(int(search_term))
    
    # Try to find by username (without @)
    if not user and search_term.startswith('@'):
        search_term = search_term[1:]
    
    if not user:
        # Search in database by username
        from database.connection import Database
        result = await Database.fetchrow(
            "SELECT * FROM users WHERE username ILIKE $1 LIMIT 1",
            f"%{search_term}%"
        )
        if result:
            user = dict(result)
    
    if not user:
        await update.message.reply_text(
            f"❌ Utilisateur non trouvé : {search_term}\n\n"
            "Essayez avec un autre terme.",
            reply_markup=admin_menus.back_to_menu_keyboard()
        )
        return SEARCH_USER
    
    # Get user stats
    stats = await queries.get_user_stats(user['id'])
    
    status = "🔒 Bloqué" if user['is_blocked'] else "✅ Actif"
    
    message = (
        f"👤 <b>Profil Utilisateur</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 <b>ID :</b> {user['telegram_id']}\n"
        f"👤 <b>Username :</b> @{user.get('username', 'N/A')}\n"
        f"📛 <b>Prénom :</b> {user.get('first_name', 'N/A')}\n"
        f"📱 <b>Téléphone :</b> {user.get('phone', 'N/A')}\n"
        f"📊 <b>Statut :</b> {status}\n\n"
        
        f"💰 <b>FINANCES</b>\n"
        f"• Solde : {format_currency(user['balance'])}\n"
        f"• Total gagné : {format_currency(stats.get('total_earned', 0))}\n\n"
        
        f"📤 <b>PARTAGES</b>\n"
        f"• Validés : {stats.get('total_shares', 0)}\n"
        f"• En attente : {stats.get('pending_shares', 0)}\n\n"
        
        f"🎁 <b>PARRAINAGE</b>\n"
        f"• Code : <code>{user['referral_code']}</code>\n"
        f"• Filleuls : {stats.get('referral_count', 0)}\n\n"
        
        f"📅 <b>Inscrit le :</b> {format_datetime(user['created_at'])}"
    )
    
    context.user_data['viewing_user_id'] = user['id']
    
    await update.message.reply_text(
        message,
        reply_markup=admin_menus.user_action_keyboard(user['id'], user['is_blocked']),
        parse_mode="HTML"
    )
    
    return ConversationHandler.END


async def block_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Block a user"""
    query = update.callback_query
    
    if not await is_authorized(update):
        return
    
    user_id = int(query.data.replace("block_", ""))
    
    success = await queries.block_user(user_id, blocked=True)
    
    if success:
        await query.answer("🔒 Utilisateur bloqué")
        
        # Update message with new status
        await query.message.edit_reply_markup(
            reply_markup=admin_menus.user_action_keyboard(user_id, True)
        )
    else:
        await query.answer("❌ Erreur", show_alert=True)


async def unblock_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unblock a user"""
    query = update.callback_query
    
    if not await is_authorized(update):
        return
    
    user_id = int(query.data.replace("unblock_", ""))
    
    success = await queries.block_user(user_id, blocked=False)
    
    if success:
        await query.answer("🔓 Utilisateur débloqué")
        
        # Update message with new status
        await query.message.edit_reply_markup(
            reply_markup=admin_menus.user_action_keyboard(user_id, False)
        )
    else:
        await query.answer("❌ Erreur", show_alert=True)


async def user_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's share history"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    user_id = int(query.data.replace("user_history_", ""))
    
    shares = await queries.get_user_shares(user_id, limit=10)
    
    if not shares:
        await query.message.edit_text(
            "📊 <b>Historique</b>\n\n"
            "Aucun partage trouvé.",
            reply_markup=admin_menus.back_to_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    message_parts = ["📊 <b>Derniers Partages</b>\n"]
    
    for share in shares:
        status_emoji = get_status_emoji(share['status'])
        message_parts.append(
            f"\n{status_emoji} {share['group_name'][:25]}\n"
            f"   └ {share['platform']} | {format_datetime(share['created_at'], False)}"
        )
    
    await query.message.edit_text(
        "\n".join(message_parts),
        reply_markup=admin_menus.back_to_menu_keyboard(),
        parse_mode="HTML"
    )


async def cancel_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel user search"""
    query = update.callback_query
    
    if query:
        await query.answer()
        await query.message.edit_text(
            "❌ Recherche annulée.",
            reply_markup=admin_menus.back_to_menu_keyboard()
        )
    
    return ConversationHandler.END
