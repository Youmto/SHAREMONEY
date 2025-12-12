"""
Service de notifications Telegram
"""
from telegram import Bot
from telegram.error import TelegramError
from typing import List, Optional
import asyncio
import logging

from config.settings import BOT_USER_TOKEN

logger = logging.getLogger(__name__)


async def notify_user(
    telegram_id: int,
    message: str,
    parse_mode: str = "HTML"
) -> bool:
    """
    Envoie une notification à un utilisateur via le bot utilisateur
    """
    if not BOT_USER_TOKEN:
        logger.error("❌ BOT_USER_TOKEN non configuré - notification impossible")
        return False
    
    try:
        logger.info(f"📤 Envoi notification à {telegram_id}...")
        bot = Bot(token=BOT_USER_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode=parse_mode
            )
        logger.info(f"✅ Notification envoyée à {telegram_id}")
        return True
    except TelegramError as e:
        logger.error(f"❌ Erreur notification {telegram_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur inattendue notification {telegram_id}: {e}")
        return False


async def notify_share_approved(telegram_id: int, amount: int, new_balance: int):
    """
    Notifie un utilisateur que son partage a été approuvé
    """
    message = f"""
✅ <b>Partage validé !</b>

💰 +{amount} FCFA crédités sur votre compte

📊 Nouveau solde : <b>{new_balance} FCFA</b>

Continuez à partager pour gagner plus ! 🚀
"""
    await notify_user(telegram_id, message)


async def notify_share_rejected(telegram_id: int, reason: str = None):
    """
    Notifie un utilisateur que son partage a été rejeté
    """
    message = f"""
❌ <b>Partage rejeté</b>

Votre preuve de partage n'a pas été validée.

"""
    if reason:
        message += f"📝 Raison : {reason}\n\n"
    
    message += """
💡 Assurez-vous que votre screenshot montre :
• Le nom du groupe
• Le nombre de membres
• Votre message avec la vidéo

Réessayez avec une nouvelle preuve !
"""
    await notify_user(telegram_id, message)


async def notify_withdrawal_completed(
    telegram_id: int, 
    amount: int, 
    payment_method: str,
    payment_details: str
):
    """
    Notifie un utilisateur que son retrait a été effectué
    """
    message = f"""
✅ <b>Paiement effectué !</b>

💰 Montant : <b>{amount} FCFA</b>
📱 Méthode : {payment_method}
📍 Envoyé à : {payment_details}

Merci de votre confiance ! 🙏
"""
    await notify_user(telegram_id, message)


async def notify_withdrawal_rejected(telegram_id: int, amount: int, reason: str = None):
    """
    Notifie un utilisateur que son retrait a été rejeté
    """
    message = f"""
❌ <b>Retrait rejeté</b>

💰 Montant : {amount} FCFA (remboursé sur votre solde)

"""
    if reason:
        message += f"📝 Raison : {reason}\n\n"
    
    message += "Veuillez vérifier vos informations et réessayer."
    await notify_user(telegram_id, message)


async def notify_new_video(telegram_id: int, video_title: str):
    """
    Notifie un utilisateur qu'une nouvelle vidéo est disponible
    """
    message = f"""
🎬 <b>Nouvelle vidéo disponible !</b>

📹 {video_title}

Partagez-la maintenant pour gagner 100 FCFA !

Tapez /video pour commencer 👇
"""
    await notify_user(telegram_id, message)


async def broadcast_message(
    user_ids: List[int],
    message: str,
    delay: float = 0.05  # Délai entre chaque envoi pour éviter le rate limiting
) -> dict:
    """
    Envoie un message broadcast à une liste d'utilisateurs
    
    Retourne des statistiques d'envoi
    """
    success = 0
    failed = 0
    
    for user_id in user_ids:
        result = await notify_user(user_id, message)
        if result:
            success += 1
        else:
            failed += 1
        
        await asyncio.sleep(delay)
    
    return {
        "total": len(user_ids),
        "success": success,
        "failed": failed
    }


async def notify_referral_bonus(telegram_id: int, amount: int, referral_name: str):
    """
    Notifie un utilisateur qu'il a reçu un bonus de parrainage
    """
    message = f"""
🎉 <b>Bonus de parrainage !</b>

👤 {referral_name} s'est inscrit avec votre code !

💰 +{amount} FCFA crédités sur votre compte

Continuez à parrainer pour gagner plus ! 🚀
"""
    await notify_user(telegram_id, message)