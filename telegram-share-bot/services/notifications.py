"""
Service de notifications Telegram - Version unifiée
Toutes les notifications sont envoyées via le BOT UTILISATEUR
"""
from telegram import Bot
from telegram.error import TelegramError
from typing import List
import asyncio

from config.settings import BOT_USER_TOKEN

# Instance unique du bot utilisateur pour les notifications
_user_bot = None

async def get_user_bot() -> Bot:
    """Retourne l'instance du bot utilisateur"""
    global _user_bot
    if _user_bot is None:
        _user_bot = Bot(token=BOT_USER_TOKEN)
    return _user_bot


async def notify_user(telegram_id: int, message: str, parse_mode: str = "HTML") -> bool:
    """
    Envoie une notification à un utilisateur via le bot utilisateur
    C'est la fonction de base utilisée par toutes les autres
    """
    try:
        bot = await get_user_bot()
        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode=parse_mode
        )
        print(f"✅ Notification envoyée à {telegram_id}")
        return True
    except TelegramError as e:
        print(f"❌ Erreur notification {telegram_id}: {e}")
        return False


async def notify_share_approved(telegram_id: int, amount: int, new_balance: int) -> bool:
    """Notifie l'utilisateur que son partage a été approuvé"""
    message = f"""
🎉 <b>PARTAGE APPROUVÉ !</b>

💰 <b>+{amount} FCFA</b> ajoutés à votre solde !

💳 Nouveau solde : <b>{new_balance} FCFA</b>

Continuez à partager pour gagner plus !
"""
    return await notify_user(telegram_id, message)


async def notify_share_rejected(telegram_id: int, reason: str = None) -> bool:
    """Notifie un utilisateur que son partage a été rejeté"""
    message = """
❌ <b>PARTAGE REJETÉ</b>

Votre preuve de partage n'a pas été validée.

"""
    if reason:
        message += f"📋 <b>Raison :</b>\n{reason}\n\n"
    
    message += "💡 Vous pouvez soumettre une nouvelle preuve conforme."
    
    return await notify_user(telegram_id, message)


async def notify_withdrawal_completed(
    telegram_id: int, 
    amount: int, 
    payment_method: str,
    payment_details: str
) -> bool:
    """Notifie un utilisateur que son retrait a été effectué"""
    message = f"""
✅ <b>Paiement effectué !</b>

💰 Montant : <b>{amount} FCFA</b>
📱 Méthode : {payment_method}
📍 Envoyé à : {payment_details}

Merci de votre confiance ! 🙏
"""
    return await notify_user(telegram_id, message)


async def notify_withdrawal_rejected(telegram_id: int, amount: int, reason: str = None) -> bool:
    """Notifie un utilisateur que son retrait a été rejeté"""
    message = f"""
❌ <b>Retrait rejeté</b>

💰 Montant : {amount} FCFA (remboursé sur votre solde)

"""
    if reason:
        message += f"📝 Raison : {reason}\n\n"
    
    message += "Veuillez vérifier vos informations et réessayer."
    return await notify_user(telegram_id, message)


async def notify_new_video(telegram_id: int, video_title: str) -> bool:
    """Notifie un utilisateur qu'une nouvelle vidéo est disponible"""
    message = f"""
🎬 <b>Nouvelle vidéo disponible !</b>

📹 {video_title}

Partagez-la maintenant pour gagner 100 FCFA !

Tapez /video pour commencer 👇
"""
    return await notify_user(telegram_id, message)


async def notify_referral_bonus(telegram_id: int, amount: int, referral_name: str) -> bool:
    """Notifie un utilisateur qu'il a reçu un bonus de parrainage"""
    message = f"""
🎉 <b>Bonus de parrainage !</b>

👤 <b>{referral_name}</b> a validé son premier partage !

💰 +{amount} FCFA crédités sur votre compte

Continuez à parrainer pour gagner plus ! 🚀
"""
    return await notify_user(telegram_id, message)


async def broadcast_message(
    user_ids: List[int],
    message: str,
    delay: float = 0.05
) -> dict:
    """Envoie un message broadcast à une liste d'utilisateurs"""
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