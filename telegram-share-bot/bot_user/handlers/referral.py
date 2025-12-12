"""
Handler pour le système de parrainage
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from database.queries import get_user_by_telegram_id
from database.connection import db
from bot_user.keyboards.menus import referral_keyboard, main_menu_keyboard
from utils.constants import ERROR_NOT_REGISTERED
from utils.helpers import format_amount
from config.settings import REFERRAL_BONUS


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /referral - Affiche le code de parrainage"""
    user = update.effective_user
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.message.delete()
        except:
            pass
    
    db_user = await get_user_by_telegram_id(user.id)
    if not db_user:
        await context.bot.send_message(
            chat_id=user.id,
            text=ERROR_NOT_REGISTERED
        )
        return
    
    # Récupérer les filleuls avec leur statut (actifs = au moins 1 partage approuvé)
    referrals = await db.fetch("""
        SELECT u.*, 
               (SELECT COUNT(*) FROM shares WHERE user_id = u.id AND status = 'approved') as approved_shares
        FROM users u 
        WHERE u.referred_by = $1
        ORDER BY u.created_at DESC
    """, db_user['id'])
    
    total_referrals = len(referrals)
    active_referrals = len([r for r in referrals if r['approved_shares'] > 0])
    referral_earnings = active_referrals * REFERRAL_BONUS
    
    # Construire le lien de parrainage
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={db_user['referral_code']}"
    
    text = f"""
👥 <b>PARRAINAGE</b>

🔗 <b>Votre lien :</b>
<code>{referral_link}</code>
👆 <i>Appuyez pour copier</i>

🎫 <b>Votre code :</b> <code>{db_user['referral_code']}</code>

━━━━━━━━━━━━━━━━━━

📊 <b>Statistiques :</b>
- Inscrits : {total_referrals}
- Actifs (1+ partage validé) : {active_referrals}
- Gains : <b>{format_amount(referral_earnings)}</b>

━━━━━━━━━━━━━━━━━━

💡 <b>Comment ça marche ?</b>
1. Partagez votre lien
2. Vos amis s'inscrivent
3. Quand ils font leur <b>premier partage validé</b>,
   vous gagnez <b>{REFERRAL_BONUS} FCFA</b> !
"""
    
    # Liste des derniers filleuls
    if referrals:
        text += "\n📋 <b>Derniers filleuls :</b>\n"
        for r in referrals[:5]:
            status = "✅" if r['approved_shares'] > 0 else "⏳"
            name = r['first_name'] or r['username'] or 'Anonyme'
            text += f"{status} {name}\n"
    
    keyboard = [
        [InlineKeyboardButton("📤 Partager mon lien", switch_inline_query=f"Gagnez de l'argent ! Inscrivez-vous : {referral_link}")],
        [InlineKeyboardButton("🏠 Menu principal", callback_data="main_menu")]
    ]
    
    await context.bot.send_message(
        chat_id=user.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


def get_referral_handlers():
    """Retourne les handlers pour le parrainage"""
    return [
        CommandHandler("referral", referral_command),
        CallbackQueryHandler(referral_command, pattern="^referral$"),
    ]