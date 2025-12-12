"""
Service de validation d'images et détection de fraudes
"""
import hashlib
from io import BytesIO
from typing import Tuple, Optional
from PIL import Image

from config.settings import MIN_IMAGE_SIZE, GROUP_REUSE_DAYS
from database.queries import (
    check_duplicate_proof, 
    check_group_recently_used,
    get_user_validation_rate,
    get_user_shares_today,
    is_group_blacklisted
)


class ValidationResult:
    def __init__(self, is_valid: bool, error: str = None, score: int = 100):
        self.is_valid = is_valid
        self.error = error
        self.score = score  # Score de confiance (0-100)


async def validate_proof_image(
    image_data: bytes,
    user_id: int,
    group_link: str,
    platform: str
) -> Tuple[ValidationResult, str]:
    """
    Valide une image de preuve et retourne le résultat + hash
    
    Vérifications:
    1. Taille de l'image
    2. Image non dupliquée
    3. Groupe non blacklisté
    4. Groupe non récemment utilisé par cet utilisateur
    5. Limite journalière non atteinte
    
    Retourne: (ValidationResult, image_hash)
    """
    
    score = 100
    
    # 1. Calculer le hash de l'image
    image_hash = hashlib.sha256(image_data).hexdigest()
    
    # 2. Vérifier la taille de l'image
    try:
        img = Image.open(BytesIO(image_data))
        width, height = img.size
        
        if width < MIN_IMAGE_SIZE or height < MIN_IMAGE_SIZE:
            return ValidationResult(
                False, 
                f"❌ Image trop petite. Minimum requis: {MIN_IMAGE_SIZE}x{MIN_IMAGE_SIZE} pixels"
            ), image_hash
    except Exception as e:
        return ValidationResult(False, "❌ Fichier image invalide"), image_hash
    
    # 3. Vérifier si l'image est dupliquée
    if await check_duplicate_proof(image_hash):
        return ValidationResult(
            False, 
            "❌ Cette capture d'écran a déjà été soumise"
        ), image_hash
    
    # 4. Vérifier si le groupe est blacklisté
    if await is_group_blacklisted(group_link):
        return ValidationResult(
            False, 
            "❌ Ce groupe est sur liste noire"
        ), image_hash
    
    # 5. Vérifier si le groupe a été utilisé récemment
    if await check_group_recently_used(user_id, group_link):
        return ValidationResult(
            False, 
            f"❌ Vous avez déjà partagé dans ce groupe ces {GROUP_REUSE_DAYS} derniers jours"
        ), image_hash
    
    # 6. Vérifier la limite journalière
    from config.settings import MAX_TELEGRAM_SHARES_PER_DAY, MAX_WHATSAPP_SHARES_PER_DAY
    
    max_shares = MAX_TELEGRAM_SHARES_PER_DAY if platform == "telegram" else MAX_WHATSAPP_SHARES_PER_DAY
    shares_today = await get_user_shares_today(user_id, platform)
    
    if shares_today >= max_shares:
        platform_name = "Telegram" if platform == "telegram" else "WhatsApp"
        return ValidationResult(
            False, 
            f"❌ Limite atteinte: {max_shares} partages {platform_name} par jour"
        ), image_hash
    
    # Calculer le score de confiance basé sur l'historique
    validation_rate = await get_user_validation_rate(user_id)
    
    # Ajuster le score basé sur l'historique
    if validation_rate >= 90:
        score = 95
    elif validation_rate >= 70:
        score = 80
    elif validation_rate >= 50:
        score = 60
    elif validation_rate > 0:
        score = 40
    else:
        score = 50  # Nouvel utilisateur
    
    return ValidationResult(True, score=score), image_hash


def validate_group_link(link: str, platform: str) -> ValidationResult:
    """
    Valide le format du lien de groupe
    """
    link = link.strip().lower()
    
    if platform == "telegram":
        # Formats acceptés pour Telegram
        valid_prefixes = [
            "https://t.me/",
            "http://t.me/",
            "t.me/",
            "https://telegram.me/",
            "@"
        ]
        
        if not any(link.startswith(prefix) for prefix in valid_prefixes):
            return ValidationResult(
                False,
                "❌ Lien Telegram invalide. Utilisez un lien comme https://t.me/groupe ou @groupe"
            )
    
    elif platform == "whatsapp":
        # Formats acceptés pour WhatsApp
        valid_prefixes = [
            "https://chat.whatsapp.com/",
            "http://chat.whatsapp.com/",
            "chat.whatsapp.com/"
        ]
        
        if not any(link.startswith(prefix) for prefix in valid_prefixes):
            return ValidationResult(
                False,
                "❌ Lien WhatsApp invalide. Utilisez un lien comme https://chat.whatsapp.com/..."
            )
    
    return ValidationResult(True)


async def calculate_auto_score(
    user_id: int,
    platform: str,
    group_link: str
) -> int:
    """
    Calcule un score automatique pour aider à la validation
    
    Score basé sur:
    - Historique de l'utilisateur
    - Plateforme
    - Nouveauté du groupe
    
    Retourne un score de 0 à 100
    """
    score = 50  # Score de base
    
    # Bonus basé sur l'historique
    validation_rate = await get_user_validation_rate(user_id)
    if validation_rate >= 90:
        score += 30
    elif validation_rate >= 70:
        score += 20
    elif validation_rate >= 50:
        score += 10
    elif validation_rate < 30 and validation_rate > 0:
        score -= 20
    
    # Vérifier si c'est un nouveau groupe (jamais utilisé par personne)
    from database.connection import db
    group_uses = await db.fetchval(
        "SELECT COUNT(*) FROM shares WHERE group_link = $1",
        group_link
    )
    
    if group_uses == 0:
        score += 10  # Bonus pour nouveau groupe
    elif group_uses > 50:
        score -= 10  # Groupe très utilisé, plus de risques
    
    return min(max(score, 0), 100)  # Clamp entre 0 et 100


class FraudDetector:
    """
    Détecteur de fraudes avancé
    """
    
    @staticmethod
    async def analyze_submission(
        user_id: int,
        image_hash: str,
        group_link: str,
        platform: str
    ) -> dict:
        """
        Analyse une soumission pour détecter les fraudes potentielles
        
        Retourne un dict avec:
        - risk_level: "low", "medium", "high"
        - flags: liste des alertes
        - recommendation: "auto_approve", "manual_review", "auto_reject"
        """
        flags = []
        risk_score = 0
        
        # 1. Vérifier le taux de validation de l'utilisateur
        validation_rate = await get_user_validation_rate(user_id)
        if validation_rate < 30 and validation_rate > 0:
            flags.append("⚠️ Faible taux de validation historique")
            risk_score += 30
        
        # 2. Vérifier le nombre de partages aujourd'hui
        shares_today = await get_user_shares_today(user_id, platform)
        if shares_today >= 4:
            flags.append("⚠️ Beaucoup de partages aujourd'hui")
            risk_score += 10
        
        # 3. Vérifier l'utilisation du groupe globalement
        from database.connection import db
        
        group_uses_24h = await db.fetchval("""
            SELECT COUNT(*) FROM shares 
            WHERE group_link = $1 AND created_at > NOW() - INTERVAL '24 hours'
        """, group_link)
        
        if group_uses_24h > 10:
            flags.append("⚠️ Groupe très utilisé ces dernières 24h")
            risk_score += 20
        
        # 4. Vérifier si l'utilisateur est nouveau
        user = await db.fetchrow(
            "SELECT created_at FROM users WHERE id = $1", user_id
        )
        if user:
            from datetime import datetime, timedelta
            if user['created_at'] > datetime.now() - timedelta(days=1):
                flags.append("ℹ️ Nouvel utilisateur (< 24h)")
                risk_score += 15
        
        # Déterminer le niveau de risque et la recommandation
        if risk_score <= 10:
            risk_level = "low"
            recommendation = "auto_approve"  # Peut être auto-approuvé
        elif risk_score <= 40:
            risk_level = "medium"
            recommendation = "manual_review"  # Revue rapide recommandée
        else:
            risk_level = "high"
            recommendation = "manual_review"  # Revue détaillée nécessaire
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "flags": flags,
            "recommendation": recommendation,
            "validation_rate": validation_rate
        }
