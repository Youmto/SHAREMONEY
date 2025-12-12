"""
Claviers et menus du bot admin
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List


def admin_main_menu() -> InlineKeyboardMarkup:
    """Menu principal admin"""
    keyboard = [
        [
            InlineKeyboardButton("⏳ Preuves en attente", callback_data="pending_shares"),
            InlineKeyboardButton("💳 Retraits", callback_data="pending_withdrawals")
        ],
        [
            InlineKeyboardButton("📹 Vidéos", callback_data="manage_videos"),
            InlineKeyboardButton("💬 Témoignages", callback_data="manage_testimonials")
        ],
        [
            InlineKeyboardButton("📚 Vidéos d'aide", callback_data="help_videos_menu"),
            InlineKeyboardButton("👥 Users", callback_data="users")
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
            InlineKeyboardButton("⚙️ Config", callback_data="settings")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def share_validation_keyboard(share_id: int) -> InlineKeyboardMarkup:
    """Clavier pour valider/rejeter un partage"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Approuver", callback_data=f"approve_{share_id}"),
            InlineKeyboardButton("❌ Rejeter", callback_data=f"reject_{share_id}")
        ],
        [
            InlineKeyboardButton("⏭️ Suivant", callback_data="next_share"),
            InlineKeyboardButton("🏠 Menu", callback_data="admin_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def rejection_reasons_keyboard(share_id: int) -> InlineKeyboardMarkup:
    """Raisons de rejet"""
    reasons = [
        ("Screenshot illisible", "illisible"),
        ("Groupe trop petit", "petit_groupe"),
        ("Vidéo non visible", "pas_video"),
        ("Groupe invalide", "invalide"),
        ("Doublon", "doublon"),
    ]
    
    keyboard = [[InlineKeyboardButton(t, callback_data=f"rr_{share_id}_{c}")] for t, c in reasons]
    keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data=f"back_{share_id}")])
    
    return InlineKeyboardMarkup(keyboard)


def withdrawal_action_keyboard(withdrawal_id: int) -> InlineKeyboardMarkup:
    """Clavier pour gérer un retrait"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Payé", callback_data=f"complete_w_{withdrawal_id}"),
            InlineKeyboardButton("❌ Rejeter", callback_data=f"reject_w_{withdrawal_id}")
        ],
        [
            InlineKeyboardButton("⏭️ Suivant", callback_data="next_withdrawal"),
            InlineKeyboardButton("🏠 Menu", callback_data="admin_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def video_management_keyboard() -> InlineKeyboardMarkup:
    """Gestion des vidéos"""
    keyboard = [
        [InlineKeyboardButton("➕ Ajouter vidéo", callback_data="add_video")],
        [InlineKeyboardButton("📋 Vidéos actives", callback_data="list_videos")],
        [InlineKeyboardButton("🏠 Menu", callback_data="admin_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def video_duration_keyboard() -> InlineKeyboardMarkup:
    """Durée de validité"""
    keyboard = [
        [
            InlineKeyboardButton("24h", callback_data="duration_24"),
            InlineKeyboardButton("48h", callback_data="duration_48")
        ],
        [
            InlineKeyboardButton("72h", callback_data="duration_72"),
            InlineKeyboardButton("1 sem", callback_data="duration_168")
        ],
        [InlineKeyboardButton("❌ Annuler", callback_data="manage_videos")]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Retour au menu"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="admin_menu")]])


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation broadcast"""
    keyboard = [
        [
            InlineKeyboardButton("📤 Envoyer", callback_data="confirm_broadcast"),
            InlineKeyboardButton("❌ Annuler", callback_data="admin_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)