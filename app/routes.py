import os
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file, Response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime
from app import db
from app.models import User, PatrolEvidence

# ============ BLUEPRINTS ============
auth_bp = Blueprint('auth', __name__)
main_bp = Blueprint('main', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'error': 'Acceso no autorizado'}), 403
        return f(*args, **kwargs)
    return decorated

# ============ AUTENTICACIÓN ============
@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('main.admin_page'))
        return redirect(url_for('main.evidence_page'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.evidence_page'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        password = request.form.get('password', '')
        user = User.query.filter_by(code=code).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            if user.role == 'admin':
                return redirect(url_for('main.admin_page'))
            return redirect(url_for('main.evidence_page'))
        flash('Código o contraseña incorrectos', 'error')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/session')
@login_required
def session_info():
    return jsonify(current_user.to_dict())

# ============ PANEL ADMIN ============
@main_bp.route('/admin')
@login_required
@admin_required
def admin_page():
    return render_template('admin.html')

@main_bp.route('/api/users', methods=['GET'])
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users])

@main_bp.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    data = request.get_json() or {}
    code = (data.get('code') or '').strip().upper()
    name = (data.get('name') or '').strip()
    password = data.get('password') or ''

    if not code or not name or not password:
        return jsonify({'error': 'Código, nombre y contraseña son obligatorios'}), 400
    if len(password) < 6:
        return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
    if User.query.filter_by(code=code).first():
        return jsonify({'error': f'El código {code} ya está registrado'}), 400

    user = User(
        code=code,
        name=name,
        unit=data.get('unit', '').strip(),
        role=data.get('role', 'guardia'),
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@main_bp.route('/api/users/<user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    new_code = (data.get('code') or '').strip().upper()
    if new_code and new_code != user.code:
        if User.query.filter_by(code=new_code).first():
            return jsonify({'error': f'El código {new_code} ya existe'}), 400
        user.code = new_code

    if data.get('name'):
        user.name = data['name'].strip()
    user.unit = (data.get('unit') or '').strip()
    if data.get('role'):
        user.role = data['role']
    if data.get('password'):
        if len(data['password']) < 6:
            return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
        user.password_hash = generate_password_hash(data['password'])

    db.session.commit()
    return jsonify(user.to_dict())

@main_bp.route('/api/users/<user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'No puedes eliminar tu propia cuenta'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'ok': True})

# ============ EVIDENCIA DE PATRULLAS ============
@main_bp.route('/evidencia')
@login_required
def evidence_page():
    """ESTA ES LA RUTA QUE FALTABA Y CAUSABA EL ERROR"""
    return render_template('patrol_evidence.html')

@main_bp.route('/api/patrol-evidence', methods=['POST'])
@login_required
def create_evidence():
    """Crear evidencia y enviarla a Google Sheets via webhook + Cloudinary"""
    from app.cloudinary_service import upload_multiple_images
    
    data = request.get_json() or {}

    if not data.get('descripcion'):
        return jsonify({'error': 'La descripción es obligatoria'}), 400
    
    photos = data.get('photos') or []
    if not photos:
        return jsonify({'error': 'Debe adjuntar al menos una foto'}), 400

    try:
        # 1. Subir imágenes a Cloudinary
        photo_urls = upload_multiple_images(photos)
        if not photo_urls:
            return jsonify({'error': 'Error al subir las imágenes'}), 500
        
        # 2. Preparar payload para Google Sheets
        payload = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_role': current_user.role,
            'user_name': current_user.name,
            'patrol_num': data.get('patrol_num', ''),
            'paquete': data.get('paquete', ''),
            'progresiva': data.get('progresiva', ''),
            'margen': data.get('margen', ''),
            'zona': data.get('zona', ''),
            'descripcion': data['descripcion'].strip(),
            'photo_urls': photo_urls
        }
        
        # 3. Enviar a Google Sheets webhook
        webhook_url = os.environ.get('GOOGLE_SHEETS_WEBHOOK_URL')
        if not webhook_url:
            return jsonify({'error': 'Webhook de Google Sheets no configurado en Render'}), 500

        response = requests.post(webhook_url, json=payload, headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            # También guardamos en la BD local para que el historial web siga funcionando
            evidence = PatrolEvidence(
                user_id=current_user.id,
                patrol_num=data.get('patrol_num', ''),
                paquete=data.get('paquete', ''),
                progresiva=data.get('progresiva', ''),
                margen=data.get('margen', ''),
                zona=data.get('zona', ''),
                descripcion=data['descripcion'].strip(),
                photos=photo_urls, # Guardamos las URLs en lugar del base64 para ahorrar espacio
                location=data.get('location')
            )
            db.session.add(evidence)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Evidencia guardada correctamente', 'photo_urls': photo_urls}), 201
        else:
            return jsonify({'error': 'Error al guardar en Google Sheets'}), 500
            
    except Exception as e:
        print(f"❌ Error creando evidencia: {e}")
        return jsonify({'error': f'Error al guardar la evidencia: {str(e)}'}), 500

@main_bp.route('/api/patrol-evidence', methods=['GET'])
@login_required
def list_evidences():
    query = PatrolEvidence.query
    if current_user.role != 'admin':
        query = query.filter(PatrolEvidence.user_id == current_user.id)
    
    # Orden ascendente (más antiguo primero)
    evidences = query.order_by(PatrolEvidence.timestamp.asc()).all()
    return jsonify([e.to_dict() for e in evidences])

@main_bp.route('/api/patrol-evidence/<evidence_id>', methods=['PUT'])
@login_required
def update_evidence(evidence_id):
    evidence = PatrolEvidence.query.get_or_404(evidence_id)
    if current_user.role != 'admin' and evidence.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403

    data = request.get_json() or {}
    for field in ['patrol_num', 'paquete', 'progresiva', 'margen', 'zona', 'descripcion', 'photos']:
        if field in data:
            setattr(evidence, field, data[field])
    
    db.session.commit()
    return jsonify(evidence.to_dict())

@main_bp.route('/api/patrol-evidence/<evidence_id>', methods=['DELETE'])
@login_required
def delete_evidence(evidence_id):
    evidence = PatrolEvidence.query.get_or_404(evidence_id)
    if current_user.role != 'admin' and evidence.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403
    db.session.delete(evidence)
    db.session.commit()
    return jsonify({'ok': True})

@main_bp.route('/api/patrol-evidence/pdf', methods=['GET'])
@login_required
def generate_pdf():
    from app.pdf_generator import generate_evidence_pdf
    
    query = PatrolEvidence.query
    if current_user.role != 'admin':
        query = query.filter(PatrolEvidence.user_id == current_user.id)
    
    evidences = query.order_by(PatrolEvidence.timestamp.asc()).all()
    
    if not evidences:
        return jsonify({'error': 'No hay evidencias para generar el PDF'}), 400
    
    pdf_buffer = generate_evidence_pdf([e.to_dict() for e in evidences], title="REPORTE SEMANAL")
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'evidencia_patrullas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )

# ============ PWA: SERVICE WORKER Y MANIFEST ============
@main_bp.route('/sw.js')
def service_worker():
    from flask import send_from_directory
    return send_from_directory(current_app.static_folder, 'sw.js', mimetype='application/javascript')

@main_bp.route('/manifest.webmanifest')
def manifest_file():
    file_path = os.path.join(current_app.root_path, '..', 'manifest.webmanifest.json')
    file_path = os.path.normpath(file_path)
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='application/manifest+json', headers={'Cache-Control': 'no-cache'})
    return 'Not found', 404