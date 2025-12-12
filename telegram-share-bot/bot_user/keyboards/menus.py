"""
Claviers et menus du bot utilisateur
"""
from telegram import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from typing import List, Optional

from config.settings import PAYMENT_METHODS, PLATFORMS, BOT_CHANNEL_LINK
from utils.constants import Callback


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Menu principal"""
    keyboard = [
        [
            InlineKeyboardButton("📹 Vidéo du jour", callback_data="video"),
            InlineKeyboardButton("💰 Mon solde", callback_data="balance")
        ],
        [
            InlineKeyboardButton("📤 Soumettre preuve", callback_data="share"),
            InlineKeyboardButton("💳 Retirer", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("👥 Parrainage", callback_data="referral"),
            InlineKeyboardButton("❓ Aide", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Clavier pour demander le numéro de téléphone"""
    keyboard = [
        [KeyboardButton("📱 Partager mon numéro", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def remove_keyboard() -> ReplyKeyboardRemove:
    """Supprime le clavier personnalisé"""
    return ReplyKeyboardRemove()


def platform_selection_keyboard() -> InlineKeyboardMarkup:
    """Sélection de la plateforme de partage"""
    keyboard = [
        [
            InlineKeyboardButton(
                f"{PLATFORMS['telegram']['emoji']} Telegram (250+ membres)",
                callback_data=Callback.PLATFORM_TELEGRAM
            )
        ],
        [
            InlineKeyboardButton(
                f"{PLATFORMS['whatsapp']['emoji']} WhatsApp (200+ membres)",
                callback_data=Callback.PLATFORM_WHATSAPP
            )
        ],
        [
            InlineKeyboardButton("🔙 Retour", callback_data=Callback.MAIN_MENU)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def testimonials_keyboard(testimonials: List[dict]) -> InlineKeyboardMarkup:
    """Sélection du message témoignage"""
    keyboard = []
    
    for i, t in enumerate(testimonials, 1):
        # Tronquer le message pour l'affichage
        preview = t['message'][:40] + "..." if len(t['message']) > 40 else t['message']
        keyboard.append([
            InlineKeyboardButton(
                f"{i}️⃣ {preview}",
                callback_data=f"{Callback.TESTIMONIAL_PREFIX}{t['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            "✏️ Écrire mon propre message",
            callback_data=Callback.CUSTOM_TESTIMONIAL
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Retour", callback_data=Callback.SHARE)
    ])
    
    return InlineKeyboardMarkup(keyboard)


def share_content_keyboard() -> InlineKeyboardMarkup:
    """Boutons après affichage du contenu à partager"""
    keyboard = [
        [
            InlineKeyboardButton("📤 J'ai partagé, soumettre ma preuve", callback_data="submit_proof")
        ],
        [
            InlineKeyboardButton("🔙 Retour", callback_data=Callback.SHARE)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def after_share_keyboard() -> InlineKeyboardMarkup:
    """Boutons après soumission d'un partage"""
    keyboard = [
        [
            InlineKeyboardButton("📤 Faire un autre partage", callback_data=Callback.SHARE),
            InlineKeyboardButton("💰 Mon solde", callback_data="balance")
        ],
        [
            InlineKeyboardButton("🏠 Menu principal", callback_data=Callback.MAIN_MENU)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def payment_methods_keyboard() -> InlineKeyboardMarkup:
    """Sélection de la méthode de paiement"""
    keyboard = []
    
    for method_id, method in PAYMENT_METHODS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{method['emoji']} {method['name']}",
                callback_data=f"{Callback.PAYMENT_METHOD_PREFIX}{method_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Retour", callback_data=Callback.MAIN_MENU)
    ])
    
    return InlineKeyboardMarkup(keyboard)


def withdrawal_amount_keyboard(balance: int) -> InlineKeyboardMarkup:
    """Sélection du montant de retrait"""
    keyboard = []
    
    # Montants prédéfinis
    amounts = [500, 1000, 2000, 5000]
    row = []
    for amount in amounts:
        if amount <= balance:
            row.append(
                InlineKeyboardButton(
                    f"{amount} FCFA",
                    callback_data=f"{Callback.AMOUNT_PREFIX}{amount}"
                )
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []
    
    if row:
        keyboard.append(row)
    
    # Option tout retirer
    if balance >= 500:
        keyboard.append([
            InlineKeyboardButton(
                f"💰 Tout retirer ({balance} FCFA)",
                callback_data=f"{Callback.AMOUNT_PREFIX}{balance}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Retour", callback_data=Callback.WITHDRAW)
    ])
    
    return InlineKeyboardMarkup(keyboard)


def withdrawal_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation du retrait"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmer", callback_data=Callback.CONFIRM_WITHDRAWAL),
            InlineKeyboardButton("❌ Annuler", callback_data=Callback.CANCEL_WITHDRAWAL)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard(callback_data: str = Callback.MAIN_MENU) -> InlineKeyboardMarkup:
    """Simple bouton retour"""
    keyboard = [
        [InlineKeyboardButton("🔙 Retour", callback_data=callback_data)]
    ]
    return InlineKeyboardMarkup(keyboard)


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Bouton annuler"""
    keyboard = [
        [InlineKeyboardButton("❌ Annuler", callback_data=Callback.MAIN_MENU)]
    ]
    return InlineKeyboardMarkup(keyboard)


def video_actions_keyboard() -> InlineKeyboardMarkup:
    """Actions sur la vidéo"""
    keyboard = [
        [
            InlineKeyboardButton("📤 Partager maintenant", callback_data=Callback.SHARE)
        ],
        [
            InlineKeyboardButton("🏠 Menu principal", callback_data=Callback.MAIN_MENU)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def video_keyboard() -> InlineKeyboardMarkup:
    """Clavier pour la vidéo du jour (alias)"""
    keyboard = [
        [
            InlineKeyboardButton("📤 Partager cette vidéo", callback_data=Callback.SHARE)
        ],
        [
            InlineKeyboardButton("💰 Mon solde", callback_data="balance"),
            InlineKeyboardButton("🏠 Menu", callback_data=Callback.MAIN_MENU)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def history_keyboard() -> InlineKeyboardMarkup:
    """Options de l'historique"""
    keyboard = [
        [
            InlineKeyboardButton("📤 Partages", callback_data="history_shares"),
            InlineKeyboardButton("💳 Retraits", callback_data="history_withdrawals")
        ],
        [
            InlineKeyboardButton("🏠 Menu principal", callback_data=Callback.MAIN_MENU)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def referral_keyboard(referral_code: str) -> InlineKeyboardMarkup:
    """Boutons pour le parrainage"""
    share_text = f"🎁 Rejoins ShareBot et gagne de l'argent en partageant des vidéos ! Utilise mon code : {referral_code}\n\n{BOT_CHANNEL_LINK}"
    
    keyboard = [
        [
            InlineKeyboardButton(
                "📤 Partager le lien",
                switch_inline_query=share_text
            )
        ],
        [
            InlineKeyboardButton("🏠 Menu principal", callback_data=Callback.MAIN_MENU)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def video_keyboard() -> InlineKeyboardMarkup:
    """Clavier pour la vidéo du jour"""
    keyboard = [
        [
            InlineKeyboardButton("📤 Partager cette vidéo", callback_data=Callback.SHARE)
        ],
        [
            InlineKeyboardButton("💰 Mon solde", callback_data="balance"),
            InlineKeyboardButton("🏠 Menu", callback_data=Callback.MAIN_MENU)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)