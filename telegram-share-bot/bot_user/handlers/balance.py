"""
Handler pour le solde et l'historique
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from database.queries import (
    get_user_by_telegram_id,
    get_user_shares_history,
    get_user_withdrawals
)
from bot_user.keyboards.menus import main_menu_keyboard, back_keyboard
from config.settings import MIN_WITHDRAWAL


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le solde de l'utilisateur"""
    user = update.effective_user
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        # Supprimer l'ancien message (peut être une vidéo)
        try:
            await query.message.delete()
        except:
            pass
    
    db_user = await get_user_by_telegram_id(user.id)
    
    if not db_user:
        await context.bot.send_message(
            chat_id=user.id,
            text="❌ Vous devez d'abord vous inscrire avec /start"
        )
        return
    
    # Calculer les stats
    shares = await get_user_shares_history(db_user['id'], limit=100)
    approved = len([s for s in shares if s['status'] == 'approved'])
    pending = len([s for s in shares if s['status'] == 'pending'])
    rejected = len([s for s in shares if s['status'] == 'rejected'])
    
    withdrawals = await get_user_withdrawals(db_user['id'], limit=100)
    total_withdrawn = sum(w['amount'] for w in withdrawals if w['status'] == 'completed')
    
    can_withdraw = "✅ Oui" if db_user['balance'] >= MIN_WITHDRAWAL else f"❌ Non (min {MIN_WITHDRAWAL} FCFA)"
    
    keyboard = [
        [
            InlineKeyboardButton("📜 Historique partages", callback_data="history_shares"),
            InlineKeyboardButton("💳 Historique retraits", callback_data="history_withdrawals")
        ],
        [
            InlineKeyboardButton("💸 Retirer", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("🏠 Menu principal", callback_data="main_menu")
        ]
    ]
    
    await context.bot.send_message(
        chat_id=user.id,
        text=f"💰 <b>VOTRE SOLDE</b>\n\n"
             f"━━━━━━━━━━━━━━━━━━\n\n"
             f"💵 Solde actuel : <b>{db_user['balance']} FCFA</b>\n"
             f"📊 Total gagné : <b>{db_user['total_earned']} FCFA</b>\n"
             f"💸 Total retiré : <b>{total_withdrawn} FCFA</b>\n\n"
             f"━━━━━━━━━━━━━━━━━━\n\n"
             f"📤 <b>Vos partages :</b>\n"
             f"   ✅ Approuvés : {approved}\n"
             f"   ⏳ En attente : {pending}\n"
             f"   ❌ Rejetés : {rejected}\n\n"
             f"━━━━━━━━━━━━━━━━━━\n\n"
             f"💳 Peut retirer : {can_withdraw}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def history_shares_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche l'historique des partages"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)
    
    if not db_user:
        return
    
    shares = await get_user_shares_history(db_user['id'], limit=10)
    
    if not shares:
        text = "📜 <b>Historique des partages</b>\n\n" \
               "Aucun partage pour le moment."
    else:
        text = "📜 <b>Historique des partages</b>\n\n"
        
        for s in shares:
            if s['status'] == 'approved':
                status = "✅"
            elif s['status'] == 'pending':
                status = "⏳"
            else:
                status = "❌"
            
            date = s['created_at'].strftime('%d/%m %H:%M')
            text += f"{status} {s['platform'].upper()} - {s['group_name'][:20]} - {date}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="balance")]]
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except:
        await query.message.delete()
        await context.bot.send_message(
            chat_id=user.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )


async def history_withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche l'historique des retraits"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)
    
    if not db_user:
        return
    
    withdrawals = await get_user_withdrawals(db_user['id'], limit=10)
    
    if not withdrawals:
        text = "💳 <b>Historique des retraits</b>\n\n" \
               "Aucun retrait pour le moment."
    else:
        text = "💳 <b>Historique des retraits</b>\n\n"
        
        for w in withdrawals:
            if w['status'] == 'completed':
                status = "✅"
            elif w['status'] == 'pending':
                status = "⏳"
            else:
                status = "❌"
            
            date = w['created_at'].strftime('%d/%m %H:%M')
            text += f"{status} {w['amount']} FCFA - {w['payment_method']} - {date}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="balance")]]
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except:
        await query.message.delete()
        await context.bot.send_message(
            chat_id=user.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )


def get_balance_handlers():
    """Retourne les handlers pour le solde"""
    return [
        CommandHandler("balance", balance_command),
        CallbackQueryHandler(balance_command, pattern="^balance$"),
        CallbackQueryHandler(history_shares_callback, pattern="^history_shares$"),
        CallbackQueryHandler(history_withdrawals_callback, pattern="^history_withdrawals$"),
    ]