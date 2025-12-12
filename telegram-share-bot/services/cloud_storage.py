"""
Service de stockage cloud pour les vidéos et images (Cloudinary)
"""
import cloudinary
import cloudinary.uploader
import tempfile
import os
import asyncio
from functools import partial

from config.settings import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET
)

# Configuration Cloudinary
if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )
    CLOUDINARY_CONFIGURED = True
else:
    CLOUDINARY_CONFIGURED = False
    print("⚠️ Cloudinary non configuré - les médias seront stockés par URL uniquement")


async def download_telegram_file(bot, file_id: str, extension: str = "mp4") -> str:
    """Télécharge un fichier Telegram et retourne le chemin local"""
    file = await bot.get_file(file_id)
    temp_dir = tempfile.mkdtemp()
    local_path = os.path.join(temp_dir, f"file_{file_id[:10]}.{extension}")
    await file.download_to_drive(local_path)
    return local_path


def _upload_sync(local_path: str, resource_type: str = "video", title: str = None) -> dict:
    """Upload synchrone vers Cloudinary"""
    try:
        import time
        public_id = f"{resource_type}_{int(time.time())}"
        if title:
            clean_title = "".join(c if c.isalnum() else "_" for c in title)[:30]
            public_id = f"{clean_title}_{int(time.time())}"
        
        folder = f"telegram_bot_{resource_type}s"
        
        result = cloudinary.uploader.upload(
            local_path, 
            resource_type=resource_type,
            folder=folder,
            public_id=public_id,
            overwrite=True
        )
        
        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "duration": result.get("duration"),
            "width": result.get("width"),
            "height": result.get("height"),
            "size": result.get("bytes"),
            "format": result.get("format"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def upload_to_cloudinary(local_path: str, resource_type: str = "video", title: str = None) -> dict:
    """Upload asynchrone vers Cloudinary"""
    if not CLOUDINARY_CONFIGURED:
        return {"success": False, "error": "Cloudinary non configuré"}
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            partial(_upload_sync, local_path, resource_type, title)
        )
        return result
    finally:
        try:
            os.remove(local_path)
            os.rmdir(os.path.dirname(local_path))
        except:
            pass


async def upload_video_from_telegram(bot, file_id: str, title: str = None) -> dict:
    """Pipeline complet : Telegram Video -> Local -> Cloudinary"""
    if not CLOUDINARY_CONFIGURED:
        return {"success": False, "error": "Cloudinary non configuré"}
    
    try:
        local_path = await download_telegram_file(bot, file_id, "mp4")
        result = await upload_to_cloudinary(local_path, "video", title)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


async def upload_image_from_telegram(bot, file_id: str, title: str = None) -> dict:
    """Pipeline complet : Telegram Image -> Local -> Cloudinary"""
    if not CLOUDINARY_CONFIGURED:
        return {"success": False, "error": "Cloudinary non configuré"}
    
    try:
        local_path = await download_telegram_file(bot, file_id, "jpg")
        result = await upload_to_cloudinary(local_path, "image", title)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


async def delete_from_cloudinary(public_id: str, resource_type: str = "video") -> bool:
    """Supprime un média de Cloudinary"""
    if not CLOUDINARY_CONFIGURED or not public_id:
        return False
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            lambda: cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        )
        return True
    except:
        return False


def is_cloudinary_configured() -> bool:
    return CLOUDINARY_CONFIGURED