-- SCRIPT DE NETTOYAGE À EXÉCUTER DANS NEON SQL CONSOLE

-- 1. Voir les vidéos actuelles
SELECT id, title, 
       CASE WHEN file_id IS NOT NULL THEN 'OUI' ELSE 'NON' END as has_file_id,
       CASE WHEN url IS NOT NULL THEN 'OUI' ELSE 'NON' END as has_url,
       is_active, expires_at 
FROM videos;

-- 2. SUPPRIMER TOUTES LES VIDÉOS (obligatoire car file_id invalides)
DELETE FROM videos;

-- 3. Vérifier que c'est vide
SELECT COUNT(*) as total_videos FROM videos;
