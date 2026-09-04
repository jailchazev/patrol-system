import cloudinary
import cloudinary.uploader
import os
import base64

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

def upload_image(base64_string):
    """Subir imagen a Cloudinary con validación de tamaño."""
    try:
        # Validar que no sea None o vacío
        if not base64_string:
            print("⚠️ Imagen base64 vacía o nula")
            return ''
        
        # Remover el prefijo data:image si existe
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Validar tamaño (máximo 10MB para evitar problemas de memoria)
        size_in_bytes = len(base64_string) * 3 / 4  # Aproximado
        if size_in_bytes > 10 * 1024 * 1024:  # 10MB
            print(f"⚠️ Imagen demasiado grande: {size_in_bytes/1024/1024:.2f}MB")
            return ''
        
        print(f" Subiendo imagen de {size_in_bytes/1024:.1f}KB a Cloudinary...")
        
        response = cloudinary.uploader.upload(
            f"data:image/jpeg;base64,{base64_string}",
            folder="patrol_evidences",
            resource_type="image",
            timeout=30  # Timeout de 30 segundos
        )
        
        url = response.get('secure_url', '')
        print(f"✅ Imagen subida: {url[:50]}...")
        return url
        
    except Exception as e:
        print(f"❌ Error crítico subiendo imagen: {str(e)}")
        # NO lanzar la excepción, retornar vacío para no matar la app
        return ''

def upload_multiple_images(base64_list):
    """Subir múltiples imágenes con manejo de errores individual."""
    urls = []
    for i, base64_string in enumerate(base64_list[:2]):
        print(f" Procesando imagen {i+1} de {min(len(base64_list), 2)}...")
        url = upload_image(base64_string)
        if url:
            urls.append(url)
        else:
            print(f"⚠️ Imagen {i+1} falló, continuando...")
    
    print(f"📊 Total imágenes subidas: {len(urls)} de {len(base64_list)}")
    return urls