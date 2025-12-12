"""
Connexion à la base de données PostgreSQL (Neon) avec reconnexion automatique
"""
import asyncpg
from contextlib import asynccontextmanager
from config.settings import DATABASE_URL


class Database:
    def __init__(self):
        self.pool = None
    
    async def connect(self):
        """Crée le pool de connexions"""
        try:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60,
                max_inactive_connection_lifetime=60
            )
            print("✅ Connecté à la base de données")
        except Exception as e:
            print(f"❌ Erreur connexion DB: {e}")
            raise
    
    async def disconnect(self):
        """Ferme le pool de connexions"""
        if self.pool:
            await self.pool.close()
            print("🔌 Déconnecté de la base de données")
    
    async def ensure_connection(self):
        """Vérifie et reconnecte si nécessaire"""
        if self.pool is None:
            await self.connect()
        else:
            try:
                async with self.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
            except:
                print("🔄 Reconnexion à la base de données...")
                try:
                    await self.pool.close()
                except:
                    pass
                self.pool = None
                await self.connect()
    
    @asynccontextmanager
    async def acquire(self):
        """Context manager pour obtenir une connexion"""
        await self.ensure_connection()
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args):
        """Exécute une requête sans retour"""
        for attempt in range(2):
            try:
                async with self.acquire() as conn:
                    return await conn.execute(query, *args)
            except Exception as e:
                if attempt == 0:
                    await self.ensure_connection()
                else:
                    raise e
    
    async def fetch(self, query: str, *args):
        """Exécute une requête et retourne les résultats"""
        for attempt in range(2):
            try:
                async with self.acquire() as conn:
                    return await conn.fetch(query, *args)
            except Exception as e:
                if attempt == 0:
                    await self.ensure_connection()
                else:
                    raise e
    
    async def fetchrow(self, query: str, *args):
        """Exécute une requête et retourne une seule ligne"""
        for attempt in range(2):
            try:
                async with self.acquire() as conn:
                    return await conn.fetchrow(query, *args)
            except Exception as e:
                if attempt == 0:
                    await self.ensure_connection()
                else:
                    raise e
    
    async def fetchval(self, query: str, *args):
        """Exécute une requête et retourne une seule valeur"""
        for attempt in range(2):
            try:
                async with self.acquire() as conn:
                    return await conn.fetchval(query, *args)
            except Exception as e:
                if attempt == 0:
                    await self.ensure_connection()
                else:
                    raise e


# Instance globale
db = Database()


async def init_database():
    """Initialise les tables de la base de données"""
    await db.connect()
    
    # Création des tables
    await db.execute("""
        -- Table des utilisateurs
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(255),
            first_name VARCHAR(255),
            phone VARCHAR(50),
            balance INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            referral_code VARCHAR(20) UNIQUE,
            referred_by INTEGER REFERENCES users(id),
            is_blocked BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Table des vidéos (avec stockage cloud)
        CREATE TABLE IF NOT EXISTS videos (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            caption TEXT NOT NULL,
            cloud_url VARCHAR(500),
            cloud_public_id VARCHAR(255),
            url VARCHAR(500),
            file_size BIGINT,
            duration INTEGER,
            width INTEGER,
            height INTEGER,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Table des messages témoignages
        CREATE TABLE IF NOT EXISTS testimonial_messages (
            id SERIAL PRIMARY KEY,
            message TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Table des partages
        CREATE TABLE IF NOT EXISTS shares (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            video_id INTEGER REFERENCES videos(id),
            platform VARCHAR(20) NOT NULL,
            testimonial_id INTEGER REFERENCES testimonial_messages(id),
            custom_testimonial TEXT,
            proof_image_file_id VARCHAR(255) NOT NULL,
            proof_image_hash VARCHAR(64) NOT NULL,
            proof_image_url VARCHAR(500),
            proof_cloud_public_id VARCHAR(255),
            group_name VARCHAR(255),
            group_link VARCHAR(500),
            group_member_count INTEGER,
            status VARCHAR(20) DEFAULT 'pending',
            rejection_reason VARCHAR(255),
            auto_score INTEGER,
            validated_by BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            validated_at TIMESTAMP
        );
        
        -- Table des retraits
        CREATE TABLE IF NOT EXISTS withdrawals (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            amount INTEGER NOT NULL,
            payment_method VARCHAR(50) NOT NULL,
            payment_details VARCHAR(255) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            rejection_reason VARCHAR(255),
            processed_by BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP
        );
        
        -- Table des groupes blacklistés
        CREATE TABLE IF NOT EXISTS blacklisted_groups (
            id SERIAL PRIMARY KEY,
            group_identifier VARCHAR(500) NOT NULL,
            reason VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Table des admins
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(255),
            role VARCHAR(50) DEFAULT 'moderator',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Table des paramètres
        CREATE TABLE IF NOT EXISTS settings (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Table des vidéos d'aide
        CREATE TABLE IF NOT EXISTS help_videos (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            video_url VARCHAR(500),
            video_file_id VARCHAR(255),
            cloud_url VARCHAR(500),
            cloud_public_id VARCHAR(255),
            thumbnail_url VARCHAR(500),
            duration INTEGER,
            display_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            views_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Index pour performances
        CREATE INDEX IF NOT EXISTS idx_shares_status ON shares(status);
        CREATE INDEX IF NOT EXISTS idx_shares_user_id ON shares(user_id);
        CREATE INDEX IF NOT EXISTS idx_shares_created_at ON shares(created_at);
        CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status);
        CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);
        CREATE INDEX IF NOT EXISTS idx_shares_proof_hash ON shares(proof_image_hash);
        CREATE INDEX IF NOT EXISTS idx_videos_active ON videos(is_active, expires_at);
    """)
    
    # Migrations - Ajouter colonnes cloud à la table videos
    try:
        await db.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS cloud_url VARCHAR(500)")
    except:
        pass
    try:
        await db.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS cloud_public_id VARCHAR(255)")
    except:
        pass
    try:
        await db.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS file_size BIGINT")
    except:
        pass
    try:
        await db.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS duration INTEGER")
    except:
        pass
    try:
        await db.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS width INTEGER")
    except:
        pass
    try:
        await db.execute("ALTER TABLE videos ADD COLUMN IF NOT EXISTS height INTEGER")
    except:
        pass
    
    # Migrations - Ajouter colonnes cloud à la table shares (preuves)
    try:
        await db.execute("ALTER TABLE shares ADD COLUMN IF NOT EXISTS proof_image_url VARCHAR(500)")
    except:
        pass
    try:
        await db.execute("ALTER TABLE shares ADD COLUMN IF NOT EXISTS proof_cloud_public_id VARCHAR(255)")
    except:
        pass
    
    # Migration - Créer la table help_videos si elle n'existe pas
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS help_videos (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                video_url VARCHAR(500),
                video_file_id VARCHAR(255),
                cloud_url VARCHAR(500),
                cloud_public_id VARCHAR(255),
                thumbnail_url VARCHAR(500),
                duration INTEGER,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                views_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except:
        pass
    
    print("✅ Tables créées avec succès")


async def insert_default_testimonials():
    """Insère les messages témoignages par défaut"""
    from config.settings import DEFAULT_TESTIMONIALS
    
    for msg in DEFAULT_TESTIMONIALS:
        existing = await db.fetchval(
            "SELECT id FROM testimonial_messages WHERE message = $1",
            msg
        )
        if not existing:
            await db.execute(
                "INSERT INTO testimonial_messages (message) VALUES ($1)",
                msg
            )
    
    print("✅ Messages témoignages initialisés")