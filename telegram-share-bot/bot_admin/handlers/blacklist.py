"""
Blacklist management handlers for admin bot
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import queries
from bot_admin.keyboards import admin_menus
from bot_admin.handlers.auth import is_authorized
from utils.helpers import truncate_text, get_platform_emoji


# Conversation states
ADD_BLACKLIST_LINK = 1
ADD_BLACKLIST_REASON = 2


async def blacklist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show blacklist management menu"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    blacklist = await queries.get_blacklist()
    
    if blacklist:
        message = (
            "🚫 <b>Liste Noire des Groupes</b>\n\n"
            f"📊 {len(blacklist)} groupes bloqués\n\n"
            "Ces groupes ne peuvent pas être utilisés pour soumettre des partages."
        )
    else:
        message = (
            "🚫 <b>Liste Noire des Groupes</b>\n\n"
            "✅ Aucun groupe bloqué."
        )
    
    await query.message.edit_text(
        message,
        reply_markup=admin_menus.blacklist_keyboard(),
        parse_mode="HTML"
    )


async def add_blacklist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add to blacklist flow"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return ConversationHandler.END
    
    await query.message.edit_text(
        "🚫 <b>Ajouter à la Liste Noire</b>\n\n"
        "📝 Envoyez le lien du groupe à bloquer :\n\n"
        "<i>Exemple : t.me/groupname ou chat.whatsapp.com/xxx</i>",
        reply_markup=admin_menus.cancel_keyboard(),
        parse_mode="HTML"
    )
    
    return ADD_BLACKLIST_LINK


async def receive_blacklist_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle blacklist link"""
    if not await is_authorized(update):
        return ConversationHandler.END
    
    link = update.message.text.strip().lower()
    
    # Determine platform
    if 't.me/' in link or 'telegram' in link or link.startswith('@'):
        platform = 'telegram'
    elif 'whatsapp' in link or 'wa.me' in link:
        platform = 'whatsapp'
    else:
        await update.message.reply_text(
            "❌ Lien non reconnu. Envoyez un lien Telegram ou WhatsApp.",
            reply_markup=admin_menus.cancel_keyboard()
        )
        return ADD_BLACKLIST_LINK
    
    context.user_data['blacklist_link'] = link
    context.user_data['blacklist_platform'] = platform
    
    await update.message.reply_text(
        f"✅ Lien reçu : {link}\n"
        f"📱 Plateforme : {platform.title()}\n\n"
        "📝 Entrez la raison du blocage (ou /skip pour passer) :",
        reply_markup=admin_menus.cancel_keyboard()
    )
    
    return ADD_BLACKLIST_REASON


async def receive_blacklist_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle blacklist reason"""
    if not await is_authorized(update):
        return ConversationHandler.END
    
    reason = update.message.text.strip()
    
    if reason == "/skip":
        reason = "Non spécifié"
    
    link = context.user_data.get('blacklist_link')
    platform = context.user_data.get('blacklist_platform')
    
    # Add to blacklist
    await queries.add_to_blacklist(link, platform, reason)
    
    await update.message.reply_text(
        f"✅ <b>Groupe Ajouté à la Liste Noire</b>\n\n"
        f"🔗 {link}\n"
        f"📱 {platform.title()}\n"
        f"💬 Raison : {reason}",
        reply_markup=admin_menus.back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    
    context.user_data.pop('blacklist_link', None)
    context.user_data.pop('blacklist_platform', None)
    
    return ConversationHandler.END


async def list_blacklist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List blacklisted groups"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    blacklist = await queries.get_blacklist()
    
    if not blacklist:
        await query.message.edit_text(
            "📋 <b>Liste Noire</b>\n\n"
            "✅ Aucun groupe bloqué.",
            reply_markup=admin_menus.blacklist_keyboard(),
            parse_mode="HTML"
        )
        return
    
    message_parts = ["📋 <b>Groupes Bloqués</b>\n"]
    
    keyboard = []
    
    for item in blacklist[:20]:  # Limit to 20
        platform_emoji = get_platform_emoji(item['platform'])
        message_parts.append(
            f"\n{platform_emoji} {truncate_text(item['group_identifier'], 40)}\n"
            f"   └ {item.get('reason', 'N/A')[:30]}"
        )
        
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ Retirer",
                callback_data=f"remove_blacklist_{item['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_blacklist")])
    keyboard.append([InlineKeyboardButton("🏠 Menu", callback_data="admin_menu")])
    
    await query.message.edit_text(
        "\n".join(message_parts),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def remove_blacklist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove from blacklist"""
    query = update.callback_query
    
    if not await is_authorized(update):
        return
    
    blacklist_id = int(query.data.replace("remove_blacklist_", ""))
    
    success = await queries.remove_from_blacklist(blacklist_id)
    
    if success:
        await query.answer("✅ Groupe retiré de la liste noire")
    else:
        await query.answer("❌ Erreur", show_alert=True)
    
    # Refresh list
    await list_blacklist_callback(update, context)


async def cancel_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel blacklist operation"""
    query = update.callback_query
    
    if query:
        await query.answer()
        await query.message.edit_text(
            "❌ Opération annulée.",
            reply_markup=admin_menus.back_to_menu_keyboard()
        )
    
    context.user_data.pop('blacklist_link', None)
    context.user_data.pop('blacklist_platform', None)
    
    return ConversationHandler.END
