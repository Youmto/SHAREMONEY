"""
Share validation handlers for admin bot
"""
from telegram import Update
from telegram.ext import ContextTypes
from database import queries
from bot_admin.keyboards import admin_menus
from bot_admin.handlers.auth import is_authorized
from utils.constants import ADMIN_MESSAGES
from utils.helpers import (
    format_datetime, time_ago, get_platform_emoji,
    calculate_approval_rate, truncate_text
)
from services.notifications import notify_share_approved, notify_share_rejected
from services.fraud_detector import REJECTION_REASONS
from config.settings import Rules


async def pending_shares_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pending command"""
    if not await is_authorized(update):
        await update.message.reply_text("🚫 Accès refusé")
        return
    
    await show_next_pending_share(update, context)


async def pending_shares_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pending shares callback"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    await show_next_pending_share(update, context, edit=True)


async def show_next_pending_share(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    """Show the next pending share for validation"""
    pending = await queries.get_pending_shares(limit=1)
    
    if not pending:
        message = ADMIN_MESSAGES['no_pending_shares']
        keyboard = admin_menus.back_to_menu_keyboard()
        
        if edit and update.callback_query:
            await update.callback_query.message.edit_text(message, reply_markup=keyboard)
        else:
            target = update.callback_query.message if update.callback_query else update.message
            await target.reply_text(message, reply_markup=keyboard)
        return
    
    share = pending[0]
    
    # Calculate user stats
    total = share.get('user_total_count', 0)
    approved = share.get('user_approved_count', 0)
    rate = calculate_approval_rate(approved, total)
    
    # Get total pending count
    all_pending = await queries.get_pending_shares(limit=100)
    pending_count = len(all_pending)
    
    message = ADMIN_MESSAGES['share_review'].format(
        share_id=share['id'],
        username=share.get('username') or share.get('first_name') or f"User #{share['user_telegram_id']}",
        history=f"{approved}/{total}",
        rate=rate,
        score=share.get('auto_score', 50),
        submitted=time_ago(share['created_at']),
        platform=get_platform_emoji(share['platform']) + " " + share['platform'].title(),
        group_name=truncate_text(share['group_name'] or "N/A", 40),
        group_link=share.get('group_link', 'N/A'),
        pending_count=pending_count
    )
    
    # Store current share ID
    context.user_data['current_share_id'] = share['id']
    
    target = update.callback_query.message if update.callback_query else update.message
    
    # Delete previous message if editing
    if edit and update.callback_query:
        try:
            await update.callback_query.message.delete()
        except:
            pass
    
    # Get proof image - prefer Cloudinary URL, fallback to file_id
    proof_image = share.get('proof_image_url') or share.get('proof_image_file_id')
    
    if proof_image:
        try:
            # Send photo with caption
            await target.reply_photo(
                photo=proof_image,
                caption=message,
                reply_markup=admin_menus.share_validation_keyboard(share['id']),
                parse_mode="HTML"
            )
            return
        except Exception as e:
            print(f"❌ Erreur affichage image: {e}")
            # Continue to text fallback
    
    # Fallback to text if no image or image fails
    await target.reply_text(
        f"{message}\n\n⚠️ Image non disponible",
        reply_markup=admin_menus.share_validation_keyboard(share['id']),
        parse_mode="HTML"
    )


async def approve_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle share approval"""
    query = update.callback_query
    await query.answer("✅ Approuvé !")
    
    if not await is_authorized(update):
        return
    
    share_id = int(query.data.replace("approve_", ""))
    admin_id = update.effective_user.id
    
    # Approve the share
    success = await queries.approve_share(share_id, admin_id)
    
    if success:
        # Get share and user info for notification
        share = await queries.get_share_by_id(share_id)
        if share:
            user = await queries.get_user_by_id(share['user_id'])
            if user:
                # Notify user (via bot utilisateur automatiquement)
                try:
                    await notify_share_approved(
                        share['user_telegram_id'],
                        Rules.REWARD_PER_SHARE,
                        user['balance']
                    )
                except Exception as e:
                    print(f"❌ Erreur notification approbation: {e}")
    
    # Show next pending share
    await show_next_pending_share(update, context, edit=False)


async def reject_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show rejection reasons"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    share_id = int(query.data.replace("reject_", ""))
    
    await query.message.edit_caption(
        caption="❌ <b>Sélectionnez le motif de rejet :</b>",
        reply_markup=admin_menus.rejection_reasons_keyboard(share_id),
        parse_mode="HTML"
    )


async def reject_with_reason_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle share rejection with reason"""
    query = update.callback_query
    
    if not await is_authorized(update):
        return
    
    # Parse callback data: reject_reason_{share_id}_{reason_id}
    parts = query.data.split("_")
    share_id = int(parts[2])
    reason_id = parts[3]
    
    # Find reason text
    reason_text = "Rejeté"
    for reason in REJECTION_REASONS:
        if reason['id'] == reason_id:
            reason_text = reason['text']
            break
    
    await query.answer(f"❌ Rejeté: {reason_text[:30]}")
    
    admin_id = update.effective_user.id
    
    # Reject the share
    success = await queries.reject_share(share_id, admin_id, reason_text)
    
    if success:
        # Get share for notification
        share = await queries.get_share_by_id(share_id)
        if share:
            # Notify user (via bot utilisateur automatiquement)
            try:
                await notify_share_rejected(
                    share['user_telegram_id'],
                    reason_text
                )
                print(f"✅ Notification rejet envoyée à {share['user_telegram_id']}")
            except Exception as e:
                print(f"❌ Erreur notification rejet: {e}")
    
    # Show next pending share
    await show_next_pending_share(update, context, edit=False)


async def skip_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip current share and show next"""
    query = update.callback_query
    await query.answer("⏭️ Passé")
    
    if not await is_authorized(update):
        return
    
    # Just show next share (current one stays in queue)
    await show_next_pending_share(update, context, edit=False)


async def check_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show group link for verification"""
    query = update.callback_query
    
    if not await is_authorized(update):
        return
    
    share_id = int(query.data.replace("check_link_", ""))
    share = await queries.get_share_by_id(share_id)
    
    if share and share.get('group_link'):
        await query.answer(f"🔗 {share['group_link']}", show_alert=True)
    else:
        await query.answer("❌ Lien non disponible", show_alert=True)


async def back_to_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to share validation view"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(update):
        return
    
    share_id = int(query.data.replace("back_to_share_", ""))
    share = await queries.get_share_by_id(share_id)
    
    if not share or share['status'] != 'pending':
        await show_next_pending_share(update, context, edit=False)
        return
    
    # Recalculate stats
    total = share.get('user_total_count', 0)
    approved = share.get('user_approved_count', 0)
    rate = calculate_approval_rate(approved, total)
    
    all_pending = await queries.get_pending_shares(limit=100)
    pending_count = len(all_pending)
    
    message = ADMIN_MESSAGES['share_review'].format(
        share_id=share['id'],
        username=share.get('username') or share.get('first_name') or f"User #{share['user_telegram_id']}",
        history=f"{approved}/{total}",
        rate=rate,
        score=share.get('auto_score', 50),
        submitted=time_ago(share['created_at']),
        platform=get_platform_emoji(share['platform']) + " " + share['platform'].title(),
        group_name=truncate_text(share['group_name'] or "N/A", 40),
        group_link=share.get('group_link', 'N/A'),
        pending_count=pending_count
    )
    
    await query.message.edit_caption(
        caption=message,
        reply_markup=admin_menus.share_validation_keyboard(share['id']),
        parse_mode="HTML"
    )