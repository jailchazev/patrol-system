"""
Generador de PDF profesional para evidencias de patrullas.
Usa ReportLab para crear PDFs con encabezado corporativo en todas las páginas.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime
import base64
import os


def generate_evidence_pdf(evidences, title="EVIDENCIA DE PATRULLAS"):
    """
    Genera un PDF profesional con:
    - Encabezado corporativo en todas las páginas
    - 3 reportes por página
    - Conteo de páginas (Página X de Y)
    - Fecha de generación
    """
    buffer = BytesIO()
    
    # Configuración del documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=25*mm,
        bottomMargin=20*mm,
        leftMargin=15*mm,
        rightMargin=15*mm
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo para el texto de evidencia
    evidence_style = ParagraphStyle(
        'EvidenceText',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    
    # Estilo para fecha/hora
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#666666'),
        spaceAfter=4
    )
    
    # Construir contenido
    story = []
    evidences_per_page = 3
    current_page_evidences = []
    
    for idx, evidence in enumerate(evidences):
        # Formatear fecha
        timestamp = evidence.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%d/%m/%Y %H:%M')
            except:
                formatted_date = timestamp
        else:
            formatted_date = 'Sin fecha'
        
        # Número de patrulla
        patrol_num = evidence.get('patrol_num', '')
        patrol_badge = f"<b>Patrulla {patrol_num}</b>" if patrol_num else ""
        
        # Texto de evidencia
        user_name = evidence.get('user_name', 'Desconocido')
        paquete = evidence.get('paquete', '—')
        progresiva = evidence.get('progresiva', '—')
        margen = evidence.get('margen', '—')
        zona = evidence.get('zona', '')
        descripcion = evidence.get('descripcion', '')
        
        evidence_text = f"{user_name}, realizó ronda por Paquete {paquete}, {progresiva}, margen {margen} {zona}. {descripcion}"
        
        # Agregar fecha y patrulla
        current_page_evidences.append(Paragraph(f"<b>{formatted_date}</b> {patrol_badge}", date_style))
        current_page_evidences.append(Spacer(1, 2*mm))
        
        # Agregar texto
        current_page_evidences.append(Paragraph(evidence_text, evidence_style))
        current_page_evidences.append(Spacer(1, 3*mm))
        
        # Agregar fotos (máximo 2)
        photos = evidence.get('photos', [])
        if photos:
            photo_data = []
            for photo_base64 in photos[:2]:
                try:
                    # Decodificar base64
                    if ',' in photo_base64:
                        photo_base64 = photo_base64.split(',')[1]
                    photo_bytes = base64.b64decode(photo_base64)
                    photo_buffer = BytesIO(photo_bytes)
                    
                    # Crear imagen con tamaño fijo
                    img = Image(photo_buffer, width=75*mm, height=50*mm)
                    photo_data.append(img)
                except Exception as e:
                    print(f"Error procesando foto: {e}")
                    continue
            
            if photo_data:
                # Crear tabla de fotos (2 columnas)
                photo_table = Table([photo_data], colWidths=[75*mm, 75*mm])
                photo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                current_page_evidences.append(photo_table)
                current_page_evidences.append(Spacer(1, 4*mm))
        
        # Separador entre evidencias
        if (idx + 1) % evidences_per_page == 0 or idx == len(evidences) - 1:
            story.extend(current_page_evidences)
            current_page_evidences = []
            
            # Agregar salto de página si no es la última
            if idx < len(evidences) - 1:
                story.append(PageBreak())
    
    # Función para agregar encabezado y pie de página
    def add_header_footer(canvas, doc):
        canvas.saveState()
        
        # Encabezado corporativo
        header_y = A4[1] - 15*mm
        
        # Línea superior
        canvas.setStrokeColor(HexColor('#000000'))
        canvas.setLineWidth(1)
        canvas.line(15*mm, header_y + 8*mm, A4[0] - 15*mm, header_y + 8*mm)
        
        # Título del proyecto (izquierda)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(15*mm, header_y + 4*mm, "SOLUCIONES INTEGRALES - PAQUETE 1")
        canvas.setFont('Helvetica', 8)
        canvas.drawString(15*mm, header_y, "QUEBRADAS SAN IDELFONSO Y SAN CARLOS")
        
        # Consorcio (centro)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawCentredString(A4[0]/2, header_y + 4*mm, "CONSORCIO BESALCO STRACON")
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(A4[0]/2, header_y, "(SEGURIDAD PATRIMONIAL)")
        
        # Fecha y página (derecha)
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(A4[0] - 15*mm, header_y + 4*mm, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
        canvas.drawRightString(A4[0] - 15*mm, header_y, f"Página {doc.page} de {doc.pageCount}")
        
        # Línea inferior del encabezado
        canvas.line(15*mm, header_y - 2*mm, A4[0] - 15*mm, header_y - 2*mm)
        
        # Título del reporte
        canvas.setFont('Helvetica-Bold', 12)
        canvas.drawCentredString(A4[0]/2, header_y - 8*mm, title)
        
        # Línea debajo del título
        canvas.line(15*mm, header_y - 10*mm, A4[0] - 15*mm, header_y - 10*mm)
        
        # Pie de página
        footer_y = 12*mm
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(HexColor('#666666'))
        canvas.drawCentredString(A4[0]/2, footer_y, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} - Sistema de Evidencia de Patrullas")
        
        canvas.restoreState()
    
    # Construir PDF
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    
    buffer.seek(0)
    return buffer