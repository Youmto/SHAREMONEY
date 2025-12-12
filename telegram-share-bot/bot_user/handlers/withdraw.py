"""
Handler pour les retraits
"""
from telegram import Update
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from database.queries import (
    get_user_by_telegram_id,
    create_withdrawal
)
from bot_user.keyboards.menus import (
    payment_methods_keyboard,
    withdrawal_amount_keyboard,
    withdrawal_confirm_keyboard,
    back_keyboard,
    cancel_keyboard,
    main_menu_keyboard
)
from utils.constants import (
    WITHDRAWAL_METHOD_MESSAGE,
    WITHDRAWAL_DETAILS_MESSAGE,
    WITHDRAWAL_AMOUNT_MESSAGE,
    WITHDRAWAL_CONFIRM_MESSAGE,
    WITHDRAWAL_SUCCESS_MESSAGE,
    ERROR_NOT_REGISTERED,
    ERROR_INSUFFICIENT_BALANCE,
    ERROR_INVALID_AMOUNT,
    ConversationState,
    Callback
)
from utils.helpers import format_amount, validate_phone_number
from config.settings import PAYMENT_METHODS, MIN_WITHDRAWAL


async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /withdraw - Démarre le processus de retrait"""
    user = update.effective_user
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        is_callback = True
    else:
        is_callback = False
    
    db_user = await get_user_by_telegram_id(user.id)
    if not db_user:
        text = ERROR_NOT_REGISTERED
        if is_callback:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return
    
    # Vérifier le solde minimum
    if db_user['balance'] < MIN_WITHDRAWAL:
        text = f"""
❌ <b>Solde insuffisant</b>

💰 Votre solde : <b>{format_amount(db_user['balance'])}</b>
📍 Minimum requis : <b>{format_amount(MIN_WITHDRAWAL)}</b>

Continuez à partager pour atteindre le minimum !
"""
        if is_callback:
            await query.edit_message_text(text, reply_markup=back_keyboard(), parse_mode="HTML")
        else:
            await update.message.reply_text(text, reply_markup=back_keyboard(), parse_mode="HTML")
        return
    
    text = WITHDRAWAL_METHOD_MESSAGE.format(
        balance=format_amount(db_user['balance'])
    )
    
    if is_callback:
        await query.edit_message_text(
            text,
            reply_markup=payment_methods_keyboard(),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=payment_methods_keyboard(),
            parse_mode="HTML"
        )


async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la sélection de la méthode de paiement"""
    query = update.callback_query
    await query.answer()
    
    # Extraire la méthode du callback
    method_id = query.data.replace(Callback.PAYMENT_METHOD_PREFIX, "")
    
    if method_id not in PAYMENT_METHODS:
        await query.edit_message_text("❌ Méthode invalide")
        return
    
    method = PAYMENT_METHODS[method_id]
    context.user_data['payment_method'] = method_id
    context.user_data['payment_method_name'] = method['name']
    context.user_data['state'] = ConversationState.WAITING_PAYMENT_DETAILS
    
    await query.edit_message_text(
        WITHDRAWAL_DETAILS_MESSAGE.format(
            method=f"{method['emoji']} {method['name']}",
            placeholder=method['placeholder']
        ),
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la réception des détails de paiement"""
    if context.user_data.get('state') != ConversationState.WAITING_PAYMENT_DETAILS:
        return
    
    details = update.message.text.strip()
    method_id = context.user_data.get('payment_method')
    
    # Validation selon la méthode
    if method_id in ['orange_money', 'mtn_money']:
        if not validate_phone_number(details):
            await update.message.reply_text(
                "❌ Numéro de téléphone invalide. Réessayez.",
                reply_markup=cancel_keyboard()
            )
            return
    elif method_id == 'bitcoin':
        if len(details) < 26 or len(details) > 62:
            await update.message.reply_text(
                "❌ Adresse Bitcoin invalide. Réessayez.",
                reply_markup=cancel_keyboard()
            )
            return
    
    context.user_data['payment_details'] = details
    
    # Passer à la sélection du montant
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)
    
    context.user_data['state'] = ConversationState.WAITING_AMOUNT
    
    await update.message.reply_text(
        WITHDRAWAL_AMOUNT_MESSAGE.format(
            balance=format_amount(db_user['balance'])
        ),
        reply_markup=withdrawal_amount_keyboard(db_user['balance']),
        parse_mode="HTML"
    )


async def select_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la sélection du montant"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)
    
    # Extraire le montant
    amount = int(query.data.replace(Callback.AMOUNT_PREFIX, ""))
    
    # Vérifications
    if amount < MIN_WITHDRAWAL:
        await query.edit_message_text(
            f"❌ Montant minimum : {format_amount(MIN_WITHDRAWAL)}",
            reply_markup=withdrawal_amount_keyboard(db_user['balance'])
        )
        return
    
    if amount > db_user['balance']:
        await query.edit_message_text(
            f"❌ Solde insuffisant. Maximum : {format_amount(db_user['balance'])}",
            reply_markup=withdrawal_amount_keyboard(db_user['balance'])
        )
        return
    
    context.user_data['amount'] = amount
    context.user_data['state'] = ConversationState.CONFIRMING_WITHDRAWAL
    
    method = PAYMENT_METHODS[context.user_data['payment_method']]
    
    await query.edit_message_text(
        WITHDRAWAL_CONFIRM_MESSAGE.format(
            amount=format_amount(amount),
            method=f"{method['emoji']} {method['name']}",
            details=context.user_data['payment_details']
        ),
        reply_markup=withdrawal_confirm_keyboard(),
        parse_mode="HTML"
    )


async def handle_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la saisie d'un montant personnalisé"""
    if context.user_data.get('state') != ConversationState.WAITING_AMOUNT:
        return
    
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)
    
    try:
        amount = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            ERROR_INVALID_AMOUNT,
            reply_markup=withdrawal_amount_keyboard(db_user['balance'])
        )
        return
    
    if amount < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"❌ Montant minimum : {format_amount(MIN_WITHDRAWAL)}",
            reply_markup=withdrawal_amount_keyboard(db_user['balance'])
        )
        return
    
    if amount > db_user['balance']:
        await update.message.reply_text(
            f"❌ Solde insuffisant. Maximum : {format_amount(db_user['balance'])}",
            reply_markup=withdrawal_amount_keyboard(db_user['balance'])
        )
        return
    
    context.user_data['amount'] = amount
    context.user_data['state'] = ConversationState.CONFIRMING_WITHDRAWAL
    
    method = PAYMENT_METHODS[context.user_data['payment_method']]
    
    await update.message.reply_text(
        WITHDRAWAL_CONFIRM_MESSAGE.format(
            amount=format_amount(amount),
            method=f"{method['emoji']} {method['name']}",
            details=context.user_data['payment_details']
        ),
        reply_markup=withdrawal_confirm_keyboard(),
        parse_mode="HTML"
    )


async def confirm_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirme et crée le retrait"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)
    
    amount = context.user_data.get('amount')
    payment_method = context.user_data.get('payment_method')
    payment_details = context.user_data.get('payment_details')
    
    # Vérification finale du solde
    if db_user['balance'] < amount:
        await query.edit_message_text(
            "❌ Solde insuffisant. Veuillez réessayer.",
            reply_markup=back_keyboard()
        )
        return
    
    # Créer le retrait
    withdrawal = await create_withdrawal(
        user_id=db_user['id'],
        amount=amount,
        payment_method=payment_method,
        payment_details=payment_details
    )
    
    await query.edit_message_text(
        WITHDRAWAL_SUCCESS_MESSAGE,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    
    # Nettoyer les données
    context.user_data.clear()


async def cancel_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annule le processus de retrait"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.clear()
    
    await query.edit_message_text(
        "❌ Retrait annulé.",
        reply_markup=main_menu_keyboard()
    )


def get_withdraw_handlers():
    """Retourne les handlers pour les retraits"""
    return [
        CommandHandler("withdraw", withdraw_command),
        CallbackQueryHandler(withdraw_command, pattern="^withdraw$"),
        CallbackQueryHandler(select_payment_method, pattern=f"^{Callback.PAYMENT_METHOD_PREFIX}"),
        CallbackQueryHandler(select_amount, pattern=f"^{Callback.AMOUNT_PREFIX}"),
        CallbackQueryHandler(confirm_withdrawal, pattern=f"^{Callback.CONFIRM_WITHDRAWAL}$"),
        CallbackQueryHandler(cancel_withdrawal, pattern=f"^{Callback.CANCEL_WITHDRAWAL}$"),
    ]
