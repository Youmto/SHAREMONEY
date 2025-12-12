"""
Fonctions utilitaires
"""
from datetime import datetime, timedelta
from typing import Optional


def format_amount(amount: int) -> str:
    """Formate un montant en FCFA"""
    return f"{amount:,}".replace(",", " ") + " FCFA"


def format_datetime(dt: datetime) -> str:
    """Formate une date/heure"""
    if dt is None:
        return "N/A"
    return dt.strftime("%d/%m/%Y à %H:%M")


def format_date(dt: datetime) -> str:
    """Formate une date"""
    if dt is None:
        return "N/A"
    return dt.strftime("%d/%m/%Y")


def time_ago(dt: datetime) -> str:
    """Retourne une durée relative (il y a X minutes/heures/jours)"""
    if dt is None:
        return "N/A"
    
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        if diff.days == 1:
            return "il y a 1 jour"
        return f"il y a {diff.days} jours"
    
    hours = diff.seconds // 3600
    if hours > 0:
        if hours == 1:
            return "il y a 1 heure"
        return f"il y a {hours} heures"
    
    minutes = diff.seconds // 60
    if minutes > 0:
        if minutes == 1:
            return "il y a 1 minute"
        return f"il y a {minutes} minutes"
    
    return "à l'instant"


def time_remaining(dt: datetime) -> str:
    """Retourne le temps restant avant une date"""
    if dt is None:
        return "N/A"
    
    now = datetime.now()
    if dt <= now:
        return "Expiré"
    
    diff = dt - now
    
    if diff.days > 0:
        hours = diff.seconds // 3600
        return f"{diff.days}j {hours}h"
    
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}min"
    
    return f"{minutes} minutes"


def truncate_text(text: str, max_length: int = 50) -> str:
    """Tronque un texte avec des points de suspension"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def escape_html(text: str) -> str:
    """Échappe les caractères HTML"""
    if text is None:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def get_status_emoji(status: str) -> str:
    """Retourne l'emoji correspondant à un statut"""
    emojis = {
        "pending": "⏳",
        "approved": "✅",
        "rejected": "❌",
        "processing": "🔄",
        "completed": "✅"
    }
    return emojis.get(status, "❓")


def get_status_text(status: str) -> str:
    """Retourne le texte correspondant à un statut"""
    texts = {
        "pending": "En attente",
        "approved": "Approuvé",
        "rejected": "Rejeté",
        "processing": "En traitement",
        "completed": "Complété"
    }
    return texts.get(status, status)


def format_phone(phone: str) -> str:
    """Formate un numéro de téléphone"""
    if phone is None:
        return "Non renseigné"
    # Masquer partiellement pour la confidentialité
    if len(phone) > 4:
        return phone[:3] + "****" + phone[-2:]
    return phone


def validate_phone_number(phone: str) -> bool:
    """Valide un numéro de téléphone basique"""
    # Nettoyer le numéro
    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Vérifier la longueur
    if len(cleaned) < 8 or len(cleaned) > 15:
        return False
    
    return True


def calculate_percentage(part: int, total: int) -> float:
    """Calcule un pourcentage"""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 1)


def generate_progress_bar(percentage: float, length: int = 10) -> str:
    """Génère une barre de progression avec des emojis"""
    filled = int(percentage / 100 * length)
    empty = length - filled
    return "🟩" * filled + "⬜" * empty


def is_valid_telegram_link(link: str) -> bool:
    """Vérifie si un lien Telegram est valide"""
    link = link.lower().strip()
    valid_prefixes = [
        "https://t.me/",
        "http://t.me/",
        "t.me/",
        "https://telegram.me/",
        "@"
    ]
    return any(link.startswith(prefix) for prefix in valid_prefixes)


def is_valid_whatsapp_link(link: str) -> bool:
    """Vérifie si un lien WhatsApp est valide"""
    link = link.lower().strip()
    valid_prefixes = [
        "https://chat.whatsapp.com/",
        "http://chat.whatsapp.com/",
        "chat.whatsapp.com/"
    ]
    return any(link.startswith(prefix) for prefix in valid_prefixes)


def normalize_link(link: str) -> str:
    """Normalise un lien pour le stockage"""
    link = link.strip()
    
    # Ajouter https:// si manquant
    if link.startswith("t.me/"):
        link = "https://" + link
    elif link.startswith("chat.whatsapp.com/"):
        link = "https://" + link
    elif link.startswith("telegram.me/"):
        link = "https://" + link
    
    # Convertir @ en lien
    if link.startswith("@"):
        link = "https://t.me/" + link[1:]
    
    return link
