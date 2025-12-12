"""
Requêtes SQL pour le bot de partage
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import secrets
import string
import hashlib

from database.connection import db
from config.settings import (
    REWARD_PER_SHARE, REFERRAL_BONUS, ShareStatus, WithdrawalStatus,
    GROUP_REUSE_DAYS, MAX_TELEGRAM_SHARES_PER_DAY, MAX_WHATSAPP_SHARES_PER_DAY
)


# ============================================
# UTILISATEURS
# ============================================

def generate_referral_code(length=8):
    """Génère un code de parrainage unique"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


async def create_user(
    telegram_id: int,
    username: str = None,
    first_name: str = None,
    referred_by_code: str = None
) -> dict:
    """Crée un nouvel utilisateur"""
    
    # Vérifier si l'utilisateur existe déjà
    existing = await get_user_by_telegram_id(telegram_id)
    if existing:
        return existing
    
    # Générer un code de parrainage unique
    referral_code = generate_referral_code()
    while await db.fetchval("SELECT id FROM users WHERE referral_code = $1", referral_code):
        referral_code = generate_referral_code()
    
    # Trouver le parrain si code fourni
    referred_by = None
    if referred_by_code:
        referrer = await db.fetchrow(
            "SELECT id FROM users WHERE referral_code = $1",
            referred_by_code
        )
        if referrer:
            referred_by = referrer['id']
    
    # Créer l'utilisateur
    user = await db.fetchrow("""
        INSERT INTO users (telegram_id, username, first_name, referral_code, referred_by)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
    """, telegram_id, username, first_name, referral_code, referred_by)
    
    # Créditer le bonus de parrainage au parrain
    if referred_by:
        await db.execute("""
            UPDATE users SET balance = balance + $1, total_earned = total_earned + $1
            WHERE id = $2
        """, REFERRAL_BONUS, referred_by)
    
    return dict(user)


async def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    """Récupère un utilisateur par son ID Telegram"""
    user = await db.fetchrow(
        "SELECT * FROM users WHERE telegram_id = $1",
        telegram_id
    )
    return dict(user) if user else None


async def get_user_by_id(user_id: int) -> Optional[dict]:
    """Récupère un utilisateur par son ID"""
    user = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    return dict(user) if user else None


async def update_user_phone(telegram_id: int, phone: str):
    """Met à jour le numéro de téléphone"""
    await db.execute(
        "UPDATE users SET phone = $1 WHERE telegram_id = $2",
        phone, telegram_id
    )


async def update_user_last_active(telegram_id: int):
    """Met à jour la dernière activité"""
    await db.execute(
        "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_id = $1",
        telegram_id
    )


async def update_user_balance(user_id: int, amount: int, add: bool = True):
    """Met à jour le solde de l'utilisateur"""
    if add:
        await db.execute("""
            UPDATE users SET balance = balance + $1, total_earned = total_earned + $1
            WHERE id = $2
        """, amount, user_id)
    else:
        await db.execute(
            "UPDATE users SET balance = balance - $1 WHERE id = $2",
            amount, user_id
        )


async def get_user_referrals(user_id: int) -> List[dict]:
    """Récupère les filleuls d'un utilisateur"""
    referrals = await db.fetch(
        "SELECT * FROM users WHERE referred_by = $1",
        user_id
    )
    return [dict(r) for r in referrals]


async def block_user(telegram_id: int, blocked: bool = True):
    """Bloque/débloque un utilisateur"""
    await db.execute(
        "UPDATE users SET is_blocked = $1 WHERE telegram_id = $2",
        blocked, telegram_id
    )


async def get_all_users(limit: int = 100, offset: int = 0) -> List[dict]:
    """Récupère tous les utilisateurs"""
    users = await db.fetch(
        "SELECT * FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        limit, offset
    )
    return [dict(u) for u in users]


async def get_users_count() -> int:
    """Compte le nombre total d'utilisateurs"""
    return await db.fetchval("SELECT COUNT(*) FROM users")


# ============================================
# VIDÉOS
# ============================================

async def create_video(
    title: str,
    caption: str,
    cloud_url: str = None,
    cloud_public_id: str = None,
    url: str = None,
    validity_hours: int = 48,
    file_size: int = None,
    duration: int = None,
    width: int = None,
    height: int = None
) -> dict:
    """Crée une nouvelle vidéo avec stockage cloud"""
    expires_at = datetime.now() + timedelta(hours=validity_hours)
    
    # Désactiver les anciennes vidéos actives
    await db.execute("UPDATE videos SET is_active = FALSE WHERE is_active = TRUE")
    
    video = await db.fetchrow("""
        INSERT INTO videos (title, caption, cloud_url, cloud_public_id, url, expires_at,
                           file_size, duration, width, height)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
    """, title, caption, cloud_url, cloud_public_id, url, expires_at,
        file_size, duration, width, height)
    
    return dict(video)


async def get_active_video() -> Optional[dict]:
    """Récupère la vidéo active du jour (avec contenu valide)"""
    video = await db.fetchrow("""
        SELECT * FROM videos 
        WHERE is_active = TRUE 
        AND expires_at > CURRENT_TIMESTAMP
        AND (cloud_url IS NOT NULL OR url IS NOT NULL)
        AND caption IS NOT NULL AND caption != ''
        ORDER BY created_at DESC
        LIMIT 1
    """)
    return dict(video) if video else None


async def get_video_by_id(video_id: int) -> Optional[dict]:
    """Récupère une vidéo par son ID"""
    video = await db.fetchrow("SELECT * FROM videos WHERE id = $1", video_id)
    return dict(video) if video else None


async def deactivate_video(video_id: int):
    """Désactive une vidéo"""
    await db.execute(
        "UPDATE videos SET is_active = FALSE WHERE id = $1",
        video_id
    )


async def get_all_videos(limit: int = 20, offset: int = 0) -> List[dict]:
    """Récupère toutes les vidéos avec pagination"""
    videos = await db.fetch(
        "SELECT * FROM videos ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        limit, offset
    )
    return [dict(v) for v in videos]


async def get_videos_count() -> int:
    """Compte le nombre total de vidéos"""
    result = await db.fetchval("SELECT COUNT(*) FROM videos")
    return result or 0


async def delete_video(video_id: int):
    """Supprime une vidéo"""
    await db.execute("DELETE FROM videos WHERE id = $1", video_id)


async def toggle_video_active(video_id: int) -> dict:
    """Active/désactive une vidéo"""
    # Si on active, désactiver les autres d'abord
    video = await get_video_by_id(video_id)
    if video and not video['is_active']:
        await db.execute("UPDATE videos SET is_active = FALSE WHERE is_active = TRUE")
    
    updated = await db.fetchrow("""
        UPDATE videos SET is_active = NOT is_active 
        WHERE id = $1 RETURNING *
    """, video_id)
    return dict(updated) if updated else None


async def extend_video_validity(video_id: int, hours: int) -> dict:
    """Prolonge la validité d'une vidéo"""
    updated = await db.fetchrow("""
        UPDATE videos SET expires_at = expires_at + ($2 * INTERVAL '1 hour')
        WHERE id = $1 RETURNING *
    """, video_id, hours)
    return dict(updated) if updated else None


# ============================================
# MESSAGES TÉMOIGNAGES
# ============================================

async def get_active_testimonials() -> List[dict]:
    """Récupère les messages témoignages actifs"""
    testimonials = await db.fetch(
        "SELECT * FROM testimonial_messages WHERE is_active = TRUE ORDER BY id"
    )
    return [dict(t) for t in testimonials]


async def create_testimonial(message: str) -> dict:
    """Crée un nouveau message témoignage"""
    testimonial = await db.fetchrow(
        "INSERT INTO testimonial_messages (message) VALUES ($1) RETURNING *",
        message
    )
    return dict(testimonial)


async def increment_testimonial_usage(testimonial_id: int):
    """Incrémente le compteur d'utilisation"""
    await db.execute(
        "UPDATE testimonial_messages SET usage_count = usage_count + 1 WHERE id = $1",
        testimonial_id
    )


async def deactivate_testimonial(testimonial_id: int):
    """Désactive un message témoignage"""
    await db.execute(
        "UPDATE testimonial_messages SET is_active = FALSE WHERE id = $1",
        testimonial_id
    )


# ============================================
# PARTAGES
# ============================================

def hash_image(image_data: bytes) -> str:
    """Génère un hash SHA256 de l'image"""
    return hashlib.sha256(image_data).hexdigest()


async def create_share(
    user_id: int,
    video_id: int,
    platform: str,
    proof_image_file_id: str,
    proof_image_hash: str,
    group_name: str,
    group_link: str,
    testimonial_id: int = None,
    custom_testimonial: str = None,
    group_member_count: int = None,
    proof_image_url: str = None,
    proof_cloud_public_id: str = None
) -> dict:
    """Crée une nouvelle soumission de partage"""
    
    share = await db.fetchrow("""
        INSERT INTO shares (
            user_id, video_id, platform, proof_image_file_id, proof_image_hash,
            group_name, group_link, testimonial_id, custom_testimonial, group_member_count,
            proof_image_url, proof_cloud_public_id
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING *
    """, user_id, video_id, platform, proof_image_file_id, proof_image_hash,
        group_name, group_link, testimonial_id, custom_testimonial, group_member_count,
        proof_image_url, proof_cloud_public_id)
    
    # Incrémenter l'utilisation du témoignage
    if testimonial_id:
        await increment_testimonial_usage(testimonial_id)
    
    return dict(share)


async def get_share_by_id(share_id: int) -> Optional[dict]:
    """Récupère un partage par son ID"""
    share = await db.fetchrow("SELECT * FROM shares WHERE id = $1", share_id)
    return dict(share) if share else None


async def get_pending_shares(limit: int = 50) -> List[dict]:
    """Récupère les partages en attente de validation"""
    shares = await db.fetch("""
        SELECT s.*, u.username, u.first_name, u.telegram_id as user_telegram_id,
               v.title as video_title
        FROM shares s
        JOIN users u ON s.user_id = u.id
        JOIN videos v ON s.video_id = v.id
        WHERE s.status = 'pending'
        ORDER BY s.created_at ASC
        LIMIT $1
    """, limit)
    return [dict(s) for s in shares]


async def approve_share(share_id: int, admin_telegram_id: int):
    """Approuve un partage et crédite l'utilisateur"""
    share = await get_share_by_id(share_id)
    if not share or share['status'] != ShareStatus.PENDING:
        return False
    
    # Mettre à jour le statut
    await db.execute("""
        UPDATE shares 
        SET status = $1, validated_by = $2, validated_at = CURRENT_TIMESTAMP
        WHERE id = $3
    """, ShareStatus.APPROVED, admin_telegram_id, share_id)
    
    # Créditer l'utilisateur
    await update_user_balance(share['user_id'], REWARD_PER_SHARE)
    
    return True


async def reject_share(share_id: int, admin_telegram_id: int, reason: str = None):
    """Rejette un partage"""
    await db.execute("""
        UPDATE shares 
        SET status = $1, validated_by = $2, validated_at = CURRENT_TIMESTAMP, rejection_reason = $3
        WHERE id = $4
    """, ShareStatus.REJECTED, admin_telegram_id, reason, share_id)


async def get_user_shares_today(user_id: int, platform: str) -> int:
    """Compte les partages de l'utilisateur aujourd'hui pour une plateforme"""
    count = await db.fetchval("""
        SELECT COUNT(*) FROM shares 
        WHERE user_id = $1 
        AND platform = $2
        AND created_at >= CURRENT_DATE
    """, user_id, platform)
    return count or 0


async def get_user_shares_history(user_id: int, limit: int = 20) -> List[dict]:
    """Récupère l'historique des partages d'un utilisateur"""
    shares = await db.fetch("""
        SELECT s.*, v.title as video_title
        FROM shares s
        JOIN videos v ON s.video_id = v.id
        WHERE s.user_id = $1
        ORDER BY s.created_at DESC
        LIMIT $2
    """, user_id, limit)
    return [dict(s) for s in shares]


async def check_duplicate_proof(proof_hash: str) -> bool:
    """Vérifie si cette preuve a déjà été soumise"""
    existing = await db.fetchval(
        "SELECT id FROM shares WHERE proof_image_hash = $1",
        proof_hash
    )
    return existing is not None


async def check_group_recently_used(user_id: int, group_link: str) -> bool:
    """Vérifie si ce groupe a été utilisé récemment par cet utilisateur"""
    days_ago = datetime.now() - timedelta(days=GROUP_REUSE_DAYS)
    existing = await db.fetchval("""
        SELECT id FROM shares 
        WHERE user_id = $1 AND group_link = $2 AND created_at > $3
    """, user_id, group_link, days_ago)
    return existing is not None


async def get_user_validation_rate(user_id: int) -> float:
    """Calcule le taux de validation d'un utilisateur"""
    stats = await db.fetchrow("""
        SELECT 
            COUNT(*) FILTER (WHERE status = 'approved') as approved,
            COUNT(*) as total
        FROM shares WHERE user_id = $1
    """, user_id)
    
    if stats['total'] == 0:
        return 0.0
    return (stats['approved'] / stats['total']) * 100


# ============================================
# RETRAITS
# ============================================

async def create_withdrawal(
    user_id: int,
    amount: int,
    payment_method: str,
    payment_details: str
) -> dict:
    """Crée une demande de retrait"""
    
    withdrawal = await db.fetchrow("""
        INSERT INTO withdrawals (user_id, amount, payment_method, payment_details)
        VALUES ($1, $2, $3, $4)
        RETURNING *
    """, user_id, amount, payment_method, payment_details)
    
    # Débiter le solde de l'utilisateur
    await update_user_balance(user_id, amount, add=False)
    
    return dict(withdrawal)


async def get_pending_withdrawals(limit: int = 50) -> List[dict]:
    """Récupère les retraits en attente"""
    withdrawals = await db.fetch("""
        SELECT w.*, u.username, u.first_name, u.telegram_id as user_telegram_id
        FROM withdrawals w
        JOIN users u ON w.user_id = u.id
        WHERE w.status = 'pending'
        ORDER BY w.created_at ASC
        LIMIT $1
    """, limit)
    return [dict(w) for w in withdrawals]


async def complete_withdrawal(withdrawal_id: int, admin_telegram_id: int):
    """Marque un retrait comme complété"""
    await db.execute("""
        UPDATE withdrawals 
        SET status = $1, processed_by = $2, processed_at = CURRENT_TIMESTAMP
        WHERE id = $3
    """, WithdrawalStatus.COMPLETED, admin_telegram_id, withdrawal_id)


async def reject_withdrawal(withdrawal_id: int, admin_telegram_id: int, reason: str = None):
    """Rejette un retrait et rembourse l'utilisateur"""
    withdrawal = await db.fetchrow(
        "SELECT * FROM withdrawals WHERE id = $1",
        withdrawal_id
    )
    
    if withdrawal:
        # Rembourser l'utilisateur
        await update_user_balance(withdrawal['user_id'], withdrawal['amount'], add=True)
        
        # Mettre à jour le statut
        await db.execute("""
            UPDATE withdrawals 
            SET status = $1, processed_by = $2, processed_at = CURRENT_TIMESTAMP, rejection_reason = $3
            WHERE id = $4
        """, WithdrawalStatus.REJECTED, admin_telegram_id, reason, withdrawal_id)


async def get_user_withdrawals(user_id: int, limit: int = 20) -> List[dict]:
    """Récupère l'historique des retraits d'un utilisateur"""
    withdrawals = await db.fetch(
        "SELECT * FROM withdrawals WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        user_id, limit
    )
    return [dict(w) for w in withdrawals]


# ============================================
# BLACKLIST
# ============================================

async def blacklist_group(group_identifier: str, reason: str = None):
    """Ajoute un groupe à la blacklist"""
    await db.execute(
        "INSERT INTO blacklisted_groups (group_identifier, reason) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        group_identifier, reason
    )


async def is_group_blacklisted(group_identifier: str) -> bool:
    """Vérifie si un groupe est blacklisté"""
    existing = await db.fetchval(
        "SELECT id FROM blacklisted_groups WHERE group_identifier = $1",
        group_identifier
    )
    return existing is not None


async def get_blacklisted_groups() -> List[dict]:
    """Récupère tous les groupes blacklistés"""
    groups = await db.fetch("SELECT * FROM blacklisted_groups ORDER BY created_at DESC")
    return [dict(g) for g in groups]


# ============================================
# STATISTIQUES
# ============================================

async def get_daily_stats() -> dict:
    """Récupère les statistiques du jour"""
    stats = await db.fetchrow("""
        SELECT
            (SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE) as new_users_today,
            (SELECT COUNT(*) FROM shares WHERE created_at >= CURRENT_DATE) as shares_today,
            (SELECT COUNT(*) FROM shares WHERE status = 'pending') as pending_shares,
            (SELECT COUNT(*) FROM shares WHERE status = 'approved' AND validated_at >= CURRENT_DATE) as approved_today,
            (SELECT COUNT(*) FROM withdrawals WHERE status = 'pending') as pending_withdrawals,
            (SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE status = 'pending') as pending_amount,
            (SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE status = 'completed' AND processed_at >= CURRENT_DATE) as paid_today,
            (SELECT COUNT(*) FROM users) as total_users
    """)
    return dict(stats)


async def get_budget_used_today() -> int:
    """Calcule le budget utilisé aujourd'hui"""
    approved = await db.fetchval("""
        SELECT COUNT(*) FROM shares 
        WHERE status = 'approved' AND validated_at >= CURRENT_DATE
    """)
    return (approved or 0) * REWARD_PER_SHARE


# ============================================
# VIDÉOS D'AIDE
# ============================================

async def get_help_videos(active_only: bool = True) -> List[dict]:
    """Récupère les vidéos d'aide"""
    if active_only:
        videos = await db.fetch("""
            SELECT * FROM help_videos 
            WHERE is_active = TRUE 
            ORDER BY display_order ASC, created_at DESC
        """)
    else:
        videos = await db.fetch("""
            SELECT * FROM help_videos 
            ORDER BY display_order ASC, created_at DESC
        """)
    return [dict(v) for v in videos]


async def get_help_video_by_id(video_id: int) -> Optional[dict]:
    """Récupère une vidéo d'aide par son ID"""
    video = await db.fetchrow("SELECT * FROM help_videos WHERE id = $1", video_id)
    return dict(video) if video else None


async def create_help_video(
    title: str,
    description: str = None,
    video_url: str = None,
    video_file_id: str = None,
    cloud_url: str = None,
    cloud_public_id: str = None,
    thumbnail_url: str = None,
    duration: int = None,
    display_order: int = 0
) -> dict:
    """Crée une nouvelle vidéo d'aide"""
    video = await db.fetchrow("""
        INSERT INTO help_videos (
            title, description, video_url, video_file_id, 
            cloud_url, cloud_public_id, thumbnail_url, duration, display_order
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
    """, title, description, video_url, video_file_id, 
        cloud_url, cloud_public_id, thumbnail_url, duration, display_order)
    return dict(video)


async def update_help_video(video_id: int, **kwargs) -> Optional[dict]:
    """Met à jour une vidéo d'aide"""
    # Construire la requête dynamiquement
    updates = []
    values = []
    i = 1
    
    allowed_fields = [
        'title', 'description', 'video_url', 'video_file_id',
        'cloud_url', 'cloud_public_id', 'thumbnail_url', 
        'duration', 'display_order', 'is_active'
    ]
    
    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ${i}")
            values.append(value)
            i += 1
    
    if not updates:
        return await get_help_video_by_id(video_id)
    
    values.append(video_id)
    query = f"UPDATE help_videos SET {', '.join(updates)} WHERE id = ${i} RETURNING *"
    
    video = await db.fetchrow(query, *values)
    return dict(video) if video else None


async def delete_help_video(video_id: int) -> bool:
    """Supprime une vidéo d'aide"""
    result = await db.execute("DELETE FROM help_videos WHERE id = $1", video_id)
    return "DELETE 1" in result


async def toggle_help_video(video_id: int) -> Optional[dict]:
    """Active/désactive une vidéo d'aide"""
    video = await db.fetchrow("""
        UPDATE help_videos 
        SET is_active = NOT is_active 
        WHERE id = $1 
        RETURNING *
    """, video_id)
    return dict(video) if video else None


async def increment_help_video_views(video_id: int):
    """Incrémente le compteur de vues"""
    await db.execute("""
        UPDATE help_videos 
        SET views_count = views_count + 1 
        WHERE id = $1
    """, video_id)


async def reorder_help_video(video_id: int, new_order: int) -> Optional[dict]:
    """Change l'ordre d'affichage d'une vidéo"""
    video = await db.fetchrow("""
        UPDATE help_videos 
        SET display_order = $1 
        WHERE id = $2 
        RETURNING *
    """, new_order, video_id)
    return dict(video) if video else None