"""
Script de diagnostic et nettoyage des vidéos
Exécutez ce script pour voir l'état actuel et nettoyer si nécessaire
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

async def diagnose():
    print("🔍 DIAGNOSTIC DES VIDÉOS")
    print("=" * 50)
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Compter les vidéos
    count = await conn.fetchval("SELECT COUNT(*) FROM videos")
    print(f"\n📊 Nombre total de vidéos: {count}")
    
    # Lister toutes les vidéos
    videos = await conn.fetch("SELECT * FROM videos ORDER BY created_at DESC")
    
    if videos:
        print("\n📹 VIDÉOS EN BASE:")
        print("-" * 50)
        for v in videos:
            print(f"\n🆔 ID: {v['id']}")
            print(f"   📝 Titre: {v['title']}")
            print(f"   ✅ Active: {v['is_active']}")
            print(f"   📦 file_id: {'✅ Présent' if v['file_id'] else '❌ Absent'}")
            if v['file_id']:
                print(f"      (début: {v['file_id'][:50]}...)")
            print(f"   🔗 URL: {'✅ Présent' if v['url'] else '❌ Absent'}")
            print(f"   📋 Caption: {'✅ Présent' if v['caption'] else '❌ Absent'}")
            print(f"   ⏰ Expire: {v['expires_at']}")
    else:
        print("\n✅ Aucune vidéo en base (c'est normal si vous venez de nettoyer)")
    
    # Vérifier les colonnes
    print("\n\n📊 STRUCTURE DE LA TABLE:")
    print("-" * 50)
    columns = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'videos'
        ORDER BY ordinal_position
    """)
    for col in columns:
        print(f"   • {col['column_name']}: {col['data_type']}")
    
    await conn.close()
    
    print("\n" + "=" * 50)
    print("🛠️ SOLUTION:")
    print("=" * 50)
    print("""
Si vous voyez des vidéos avec file_id, elles ont probablement
été uploadées via le bot ADMIN et ne fonctionneront pas.

EXÉCUTEZ CE SQL DANS NEON CONSOLE:
----------------------------------
DELETE FROM videos;
----------------------------------

Puis ajoutez une nouvelle vidéo via le BOT UTILISATEUR:
1. Ouvrez le bot UTILISATEUR (pas admin!)
2. Tapez /addvideo
3. Envoyez votre vidéo
4. Suivez les étapes
""")


async def clean():
    """Nettoie toutes les vidéos"""
    print("🧹 NETTOYAGE DES VIDÉOS")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    result = await conn.execute("DELETE FROM videos")
    print(f"✅ {result}")
    
    await conn.close()
    print("✅ Toutes les vidéos ont été supprimées")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        asyncio.run(clean())
    else:
        asyncio.run(diagnose())
