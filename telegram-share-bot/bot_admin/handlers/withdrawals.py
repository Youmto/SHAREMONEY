"""
Withdrawal management handlers for admin bot
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import queries
from bot_admin.keyboards import admin_menus
from bot_admin.handlers.auth import is_authorized
from utils.constants import ADMIN_MESSAGES
from utils.helpers import format_currency, time_ago
from services.notifications import notify_withdrawal_completed, notify_withdrawal_rejected
from config.settings import PAYMENT_METHODS


# Conversation states
REJECTION_REASON = 1


async def withdrawals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /withdrawals command"""
    if not await is_authorized(update):
        await update.message.reply_text("🚫 Accès refusé")
        return
    
    await show_next_withdrawal(update, context)


async def withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawals callback"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    await show_next_withdrawal(update, context, edit=True)


async def show_next_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    """Show the next pending withdrawal"""
    pending = await queries.get_pending_withdrawals(limit=1)
    
    if not pending:
        message = ADMIN_MESSAGES['no_pending_withdrawals']
        keyboard = admin_menus.back_to_menu_keyboard()
        
        if edit and update.callback_query:
            await update.callback_query.message.edit_text(message, reply_markup=keyboard)
        else:
            target = update.callback_query.message if update.callback_query else update.message
            await target.reply_text(message, reply_markup=keyboard)
        return
    
    withdrawal = pending[0]
    
    # Get payment method info
    method_id = withdrawal['payment_method']
    method = PAYMENT_METHODS.get(method_id, {})
    method_name = f"{method.get('emoji', '')} {method.get('name', method_id)}"
    
    # Get total pending count
    all_pending = await queries.get_pending_withdrawals(limit=100)
    pending_count = len(all_pending)
    
    message = ADMIN_MESSAGES['withdrawal_review'].format(
        withdrawal_id=withdrawal['id'],
        username=withdrawal.get('username') or withdrawal.get('first_name') or f"User #{withdrawal['user_telegram_id']}",
        amount=format_currency(withdrawal['amount']),
        method=method_name,
        details=withdrawal['payment_details'],
        requested=time_ago(withdrawal['created_at']),
        pending_count=pending_count
    )
    
    # Store current withdrawal ID
    context.user_data['current_withdrawal_id'] = withdrawal['id']
    
    if edit and update.callback_query:
        await update.callback_query.message.edit_text(
            message,
            reply_markup=admin_menus.withdrawal_validation_keyboard(withdrawal['id']),
            parse_mode="HTML"
        )
    else:
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(
            message,
            reply_markup=admin_menus.withdrawal_validation_keyboard(withdrawal['id']),
            parse_mode="HTML"
        )


async def pay_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark withdrawal as paid"""
    query = update.callback_query
    
    if not await is_authorized(update):
        return
    
    withdrawal_id = int(query.data.replace("pay_", ""))
    admin_id = update.effective_user.id
    
    # Get withdrawal info before completing
    withdrawal = await queries.get_withdrawal_by_id(withdrawal_id)
    
    if not withdrawal:
        await query.answer("❌ Retrait non trouvé", show_alert=True)
        return
    
    # Complete the withdrawal
    success = await queries.complete_withdrawal(withdrawal_id, admin_id)
    
    if success:
        await query.answer("✅ Marqué comme payé !")
        
        # Get payment method info
        method = PAYMENT_METHODS.get(withdrawal['payment_method'], {})
        
        # Notify user
        try:
            await notify_withdrawal_completed(
                context.bot,
                withdrawal['user_telegram_id'],
                withdrawal['amount'],
                method.get('name', withdrawal['payment_method']),
                withdrawal['payment_details']
            )
        except Exception:
            pass
    else:
        await query.answer("❌ Erreur lors du traitement", show_alert=True)
    
    # Show next withdrawal
    await show_next_withdrawal(update, context, edit=False)


async def reject_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start withdrawal rejection flow"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    withdrawal_id = int(query.data.replace("reject_withdrawal_", ""))
    context.user_data['rejecting_withdrawal_id'] = withdrawal_id
    
    await query.message.edit_text(
        "❌ <b>Rejet du retrait</b>\n\n"
        "📝 Entrez le motif de rejet :\n"
        "(ou /skip pour utiliser un motif par défaut)",
        reply_markup=admin_menus.cancel_keyboard(),
        parse_mode="HTML"
    )
    
    return REJECTION_REASON


async def withdrawal_rejection_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal rejection reason"""
    if not await is_authorized(update):
        return ConversationHandler.END
    
    reason = update.message.text.strip()
    
    if reason == "/skip":
        reason = "Informations de paiement invalides"
    
    withdrawal_id = context.user_data.get('rejecting_withdrawal_id')
    admin_id = update.effective_user.id
    
    # Get withdrawal info
    withdrawal = await queries.get_withdrawal_by_id(withdrawal_id)
    
    if not withdrawal:
        await update.message.reply_text("❌ Retrait non trouvé")
        return ConversationHandler.END
    
    # Reject and refund
    success = await queries.reject_withdrawal(withdrawal_id, admin_id, reason)
    
    if success:
        await update.message.reply_text(f"✅ Retrait rejeté et {format_currency(withdrawal['amount'])} remboursé")
        
        # Notify user
        try:
            await notify_withdrawal_rejected(
                context.bot,
                withdrawal['user_telegram_id'],
                withdrawal['amount'],
                reason
            )
        except Exception:
            pass
    else:
        await update.message.reply_text("❌ Erreur lors du rejet")
    
    # Clear context
    context.user_data.pop('rejecting_withdrawal_id', None)
    
    # Show next withdrawal
    await show_next_withdrawal(update, context)
    
    return ConversationHandler.END


async def skip_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip current withdrawal"""
    query = update.callback_query
    await query.answer("⏭️ Passé")
    
    if not await is_authorized(update):
        return
    
    await show_next_withdrawal(update, context, edit=False)


async def cancel_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel rejection"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.pop('rejecting_withdrawal_id', None)
    
    await show_next_withdrawal(update, context, edit=True)
    
    return ConversationHandler.END
