"""
Servicio de subida de imágenes a Cloudinary.
"""

import cloudinary
import cloudinary.uploader
import os


# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)


def upload_image(base64_string):
    """Subir imagen base64 a Cloudinary."""
    try:
        response = cloudinary.uploader.upload(
            base64_string,
            folder="patrol_evidences",
            resource_type="image"
        )
        return response.get('secure_url', '')
    except Exception as e:
        print(f"❌ Error subiendo imagen: {e}")
        return ''


def upload_multiple_images(base64_list):
    """Subir múltiples imágenes."""
    urls = []
    for base64_string in base64_list[:2]:
        url = upload_image(base64_string)
        if url:
            urls.append(url)
    return urls