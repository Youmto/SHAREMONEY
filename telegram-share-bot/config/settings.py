"""
Configuration principale du Bot de Partage
"""
import os
from dotenv import load_dotenv

load_dotenv()

# === TOKENS TELEGRAM ===
BOT_USER_TOKEN = os.getenv("BOT_USER_TOKEN", "8528296334:AAHcG-X_mmYg3EyutP1DBLmf74S0CFKIC9A")
BOT_ADMIN_TOKEN = os.getenv("BOT_ADMIN_TOKEN", "8307008390:AAEmfdlxTj6ciHytV8WvUgrKyeHiqZi8b3w")

# === BASE DE DONNÉES ===
DATABASE_URL = os.getenv("DATABASE_URL", "psql 'postgresql://neondb_owner:npg_w4ckLUKW5yPQ@ep-blue-frog-a2uzo6ke-pooler.eu-central-1.aws.neon.tech/bot%20ads?sslmode=require&channel_binding=require'")

# === CONFIGURATION ÉCONOMIQUE ===
REWARD_PER_SHARE = 100  # FCFA par partage validé
REFERRAL_BONUS = 50  # FCFA par filleul inscrit
MIN_WITHDRAWAL = 500  # FCFA minimum pour retirer
WITHDRAWAL_DELAY_HOURS = 24  # Délai de traitement

# === LIMITES DE PARTAGE ===
MAX_TELEGRAM_SHARES_PER_DAY = 10
MAX_WHATSAPP_SHARES_PER_DAY = 10
MIN_TELEGRAM_MEMBERS = 250
MIN_WHATSAPP_MEMBERS = 200
VIDEO_VALIDITY_HOURS = 48

# === LIENS ===
BOT_CHANNEL_LINK = "https://t.me/+Hzohxyi7XFY5ZWJk"

# === ADMINS (Telegram IDs) ===
ADMIN_IDS = [
    int(id.strip()) 
    for id in os.getenv("ADMIN_IDS", "").split(",") 
    if id.strip()
]

# === MÉTHODES DE PAIEMENT ===
PAYMENT_METHODS = {
    "orange_money": {
        "name": "Orange Money",
        "emoji": "🟠",
        "placeholder": "Numéro Orange Money (ex: 691234567)"
    },
    "mtn_money": {
        "name": "MTN Money", 
        "emoji": "🟡",
        "placeholder": "Numéro MTN Money (ex: 671234567)"
    },
    "binance": {
        "name": "Binance",
        "emoji": "🔶",
        "placeholder": "Binance ID ou Email"
    },
    "bitcoin": {
        "name": "Bitcoin",
        "emoji": "₿",
        "placeholder": "Adresse Bitcoin (BTC)"
    }
}

# === PLATEFORMES DE PARTAGE ===
PLATFORMS = {
    "telegram": {
        "name": "Telegram",
        "emoji": "📘",
        "min_members": MIN_TELEGRAM_MEMBERS,
        "max_shares": MAX_TELEGRAM_SHARES_PER_DAY
    },
    "whatsapp": {
        "name": "WhatsApp",
        "emoji": "💚",
        "min_members": MIN_WHATSAPP_MEMBERS,
        "max_shares": MAX_WHATSAPP_SHARES_PER_DAY
    }
}

# === STATUTS ===
class ShareStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class WithdrawalStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"

# === MESSAGES TÉMOIGNAGES PAR DÉFAUT ===
DEFAULT_TESTIMONIALS = [
    "✅ Ça fonctionne parfait ! J'ai déjà retiré de l'argent. Rejoignez maintenant : {link}",
    "💰 Je confirme, c'est fiable ! Paiement reçu en 24h. Inscrivez-vous : {link}",
    "🎯 Meilleure décision ! Simple et rapide. Rejoignez : {link}",
    "🔥 100% légit ! J'ai gagné en partageant simplement. Cliquez ici : {link}",
    "⭐ Je recommande ! Paiement rapide et sécurisé. Rejoignez-nous : {link}"
]

# === CONFIGURATION BUDGET (optionnel) ===
DAILY_BUDGET_LIMIT = int(os.getenv("DAILY_BUDGET_LIMIT", "50000"))  # FCFA
MONTHLY_BUDGET_LIMIT = int(os.getenv("MONTHLY_BUDGET_LIMIT", "1000000"))  # FCFA

# === ANTI-FRAUDE ===
MIN_IMAGE_SIZE = 500  # pixels minimum
GROUP_REUSE_DAYS = 7  # jours avant de réutiliser un groupe
MIN_DELAY_BETWEEN_SHARES = 30  # minutes entre partages

# === CLOUDINARY (Stockage vidéos) ===
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
