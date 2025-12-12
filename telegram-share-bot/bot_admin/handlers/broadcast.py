"""
Broadcast handlers for admin bot
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import queries
from database.connection import Database
from bot_admin.keyboards import admin_menus
from bot_admin.handlers.auth import is_authorized
from services.notifications import broadcast_message


# Conversation states
BROADCAST_MESSAGE = 1
BROADCAST_CONFIRM = 2


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast flow"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return ConversationHandler.END
    
    # Get user count
    stats = await queries.get_global_stats()
    
    await query.message.edit_text(
        f"📢 <b>Message Broadcast</b>\n\n"
        f"👥 Destinataires : {stats.get('total_users', 0)} utilisateurs\n\n"
        f"📝 Envoyez le message à diffuser :\n\n"
        f"<i>Formatage HTML supporté : &lt;b&gt;gras&lt;/b&gt;, &lt;i&gt;italique&lt;/i&gt;</i>",
        reply_markup=admin_menus.cancel_keyboard(),
        parse_mode="HTML"
    )
    
    return BROADCAST_MESSAGE


async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message"""
    if not await is_authorized(update):
        return ConversationHandler.END
    
    message = update.message.text.strip()
    
    if len(message) < 10:
        await update.message.reply_text(
            "❌ Message trop court.",
            reply_markup=admin_menus.cancel_keyboard()
        )
        return BROADCAST_MESSAGE
    
    context.user_data['broadcast_message'] = message
    
    # Get user count
    stats = await queries.get_global_stats()
    
    await update.message.reply_text(
        f"📋 <b>Confirmation</b>\n\n"
        f"📝 <b>Message :</b>\n{message[:500]}\n\n"
        f"👥 <b>Destinataires :</b> {stats.get('total_users', 0)} utilisateurs\n\n"
        f"⚠️ Cette action est irréversible.",
        reply_markup=admin_menus.confirm_broadcast_keyboard(),
        parse_mode="HTML"
    )
    
    return BROADCAST_CONFIRM


async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute broadcast"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return ConversationHandler.END
    
    message = context.user_data.get('broadcast_message')
    
    if not message:
        await query.message.edit_text(
            "❌ Message non trouvé.",
            reply_markup=admin_menus.back_to_menu_keyboard()
        )
        return ConversationHandler.END
    
    # Get all user IDs
    users = await Database.fetch("SELECT telegram_id FROM users WHERE is_blocked = FALSE")
    user_ids = [u['telegram_id'] for u in users]
    
    await query.message.edit_text(
        f"📤 <b>Envoi en cours...</b>\n\n"
        f"0/{len(user_ids)} envoyés",
        parse_mode="HTML"
    )
    
    # Send broadcast
    result = await broadcast_message(query.bot, user_ids, message)
    
    await query.message.edit_text(
        f"✅ <b>Broadcast Terminé !</b>\n\n"
        f"📊 <b>Résultats :</b>\n"
        f"• ✅ Envoyés : {result['success']}\n"
        f"• ❌ Échecs : {result['failed']}\n"
        f"• 📊 Total : {len(user_ids)}",
        reply_markup=admin_menus.back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    
    context.user_data.pop('broadcast_message', None)
    
    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel broadcast"""
    query = update.callback_query
    
    if query:
        await query.answer()
        await query.message.edit_text(
            "❌ Broadcast annulé.",
            reply_markup=admin_menus.back_to_menu_keyboard()
        )
    
    context.user_data.pop('broadcast_message', None)
    
    return ConversationHandler.END
