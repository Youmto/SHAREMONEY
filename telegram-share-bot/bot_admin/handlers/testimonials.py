"""
Testimonial management handlers for admin bot
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import queries
from bot_admin.keyboards import admin_menus
from bot_admin.handlers.auth import is_authorized


# Conversation states
ADD_TESTIMONIAL = 1


async def testimonials_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show testimonial management menu"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    testimonials = await queries.get_testimonials()
    
    if testimonials:
        message = (
            "💬 <b>Gestion des Témoignages</b>\n\n"
            f"📊 {len(testimonials)} messages actifs\n\n"
            "Ces messages sont proposés aux utilisateurs pour accompagner leurs partages."
        )
    else:
        message = (
            "💬 <b>Gestion des Témoignages</b>\n\n"
            "⚠️ Aucun message de témoignage.\n"
            "Ajoutez des messages pour que les utilisateurs puissent les utiliser."
        )
    
    await query.message.edit_text(
        message,
        reply_markup=admin_menus.testimonial_management_keyboard(),
        parse_mode="HTML"
    )


async def add_testimonial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add testimonial flow"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return ConversationHandler.END
    
    await query.message.edit_text(
        "➕ <b>Ajouter un Témoignage</b>\n\n"
        "📝 Envoyez le message de témoignage.\n\n"
        "<i>Exemple :</i>\n"
        "✅ Ça fonctionne vraiment ! J'ai déjà reçu plusieurs paiements. Rejoignez-nous :",
        reply_markup=admin_menus.cancel_keyboard(),
        parse_mode="HTML"
    )
    
    return ADD_TESTIMONIAL


async def receive_testimonial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new testimonial message"""
    if not await is_authorized(update):
        return ConversationHandler.END
    
    message = update.message.text.strip()
    
    if len(message) < 20:
        await update.message.reply_text(
            "❌ Message trop court (min 20 caractères).",
            reply_markup=admin_menus.cancel_keyboard()
        )
        return ADD_TESTIMONIAL
    
    if len(message) > 500:
        await update.message.reply_text(
            "❌ Message trop long (max 500 caractères).",
            reply_markup=admin_menus.cancel_keyboard()
        )
        return ADD_TESTIMONIAL
    
    # Create testimonial
    testimonial = await queries.create_testimonial(message)
    
    if testimonial:
        await update.message.reply_text(
            f"✅ <b>Témoignage Ajouté !</b>\n\n"
            f"📝 {message[:100]}...\n\n"
            f"Les utilisateurs peuvent maintenant utiliser ce message.",
            reply_markup=admin_menus.back_to_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "❌ Erreur lors de la création.",
            reply_markup=admin_menus.back_to_menu_keyboard()
        )
    
    return ConversationHandler.END


async def list_testimonials_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all testimonials"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    testimonials = await queries.get_testimonials()
    
    if not testimonials:
        await query.message.edit_text(
            "📋 <b>Liste des Témoignages</b>\n\n"
            "Aucun témoignage trouvé.",
            reply_markup=admin_menus.testimonial_management_keyboard(),
            parse_mode="HTML"
        )
        return
    
    message_parts = ["📋 <b>Liste des Témoignages</b>\n"]
    
    keyboard = []
    
    for i, t in enumerate(testimonials, 1):
        message_parts.append(
            f"\n<b>{i}.</b> {t['message'][:80]}...\n"
            f"   📊 Utilisé : {t['usage_count']} fois"
        )
        
        # Add delete button
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ Supprimer #{i}",
                callback_data=f"delete_testimonial_{t['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_testimonials")])
    keyboard.append([InlineKeyboardButton("🏠 Menu", callback_data="admin_menu")])
    
    await query.message.edit_text(
        "\n".join(message_parts),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def delete_testimonial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a testimonial"""
    query = update.callback_query
    
    if not await is_authorized(update):
        return
    
    testimonial_id = int(query.data.replace("delete_testimonial_", ""))
    
    success = await queries.delete_testimonial(testimonial_id)
    
    if success:
        await query.answer("✅ Témoignage supprimé")
    else:
        await query.answer("❌ Erreur", show_alert=True)
    
    # Refresh list
    await list_testimonials_callback(update, context)


async def cancel_testimonial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel testimonial creation"""
    query = update.callback_query
    
    if query:
        await query.answer()
        await query.message.edit_text(
            "❌ Création annulée.",
            reply_markup=admin_menus.back_to_menu_keyboard()
        )
    
    return ConversationHandler.END
