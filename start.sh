#!/bin/bash

# ==========================================
# 🚀 Script de Inicio - Seguridad PWA
# ==========================================

echo "🔍 Verificando entorno..."

# 1. Verificar si existe el entorno virtual
if [ -d "venv" ]; then
    echo "✅ Entorno virtual encontrado. Activando..."
    # En Git Bash (Windows) se usa Scripts en lugar de bin
    source venv/Scripts/activate
else
    echo "⚠️ No se encontró la carpeta 'venv'. Usando Python global..."
fi

# 2. Verificar que exista el archivo principal
if [ ! -f "wsgi.py" ]; then
    echo "❌ Error: No se encontró 'wsgi.py'. Asegúrate de estar en la carpeta correcta (/c/security-pwa/)."
    exit 1
fi

# 3. Iniciar la aplicación
echo ""
echo "=========================================="
echo "️  INICIANDO SISTEMA DE VIGILANCIA"
echo "=========================================="
echo "🌐 URL Local: http://localhost:5000"
echo "📱 URL Red:   http://$(hostname -I | awk '{print $1}'):5000"
echo "💡 Presiona Ctrl + C para detener"
echo "=========================================="
echo ""

# Ejecutar Flask
python wsgi.py