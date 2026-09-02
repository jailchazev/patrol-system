"""
Generador de PDF profesional para evidencias de patrullas.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_JUSTIFY
from io import BytesIO
from datetime import datetime
import base64


def generate_evidence_pdf(evidences, title="EVIDENCIA DE PATRULLAS"):
    """Genera PDF con encabezado corporativo en todas las páginas."""
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=25*mm,
        bottomMargin=20*mm,
        leftMargin=15*mm,
        rightMargin=15*mm
    )
    
    styles = getSampleStyleSheet()
    
    evidence_style = ParagraphStyle(
        'EvidenceText',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#666666'),
        spaceAfter=4
    )
    
    story = []
    evidences_per_page = 3
    current_page_evidences = []
    
    for idx, evidence in enumerate(evidences):
        timestamp = evidence.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%d/%m/%Y %H:%M')
            except:
                formatted_date = timestamp
        else:
            formatted_date = 'Sin fecha'
        
        patrol_num = evidence.get('patrol_num', '')
        patrol_badge = f"<b>Patrulla {patrol_num}</b>" if patrol_num else ""
        
        user_name = evidence.get('user_name', 'Desconocido')
        paquete = evidence.get('paquete', '—')
        progresiva = evidence.get('progresiva', '—')
        margen = evidence.get('margen', '—')
        zona = evidence.get('zona', '')
        descripcion = evidence.get('descripcion', '')
        
        evidence_text = f"{user_name}, realizó ronda por Paquete {paquete}, {progresiva}, margen {margen} {zona}. {descripcion}"
        
        current_page_evidences.append(Paragraph(f"<b>{formatted_date}</b> {patrol_badge}", date_style))
        current_page_evidences.append(Spacer(1, 2*mm))
        current_page_evidences.append(Paragraph(evidence_text, evidence_style))
        current_page_evidences.append(Spacer(1, 3*mm))
        
        photos = evidence.get('photos', [])
        if photos:
            photo_data = []
            for photo_base64 in photos[:2]:
                try:
                    if ',' in photo_base64:
                        photo_base64 = photo_base64.split(',')[1]
                    photo_bytes = base64.b64decode(photo_base64)
                    photo_buffer = BytesIO(photo_bytes)
                    img = Image(photo_buffer, width=75*mm, height=50*mm)
                    photo_data.append(img)
                except Exception as e:
                    print(f"Error procesando foto: {e}")
                    continue
            
            if photo_data:
    # Si hay 2 fotos, ponerlas lado a lado con espacio
    if len(photo_data) == 2:
        photo_table = Table([photo_data], colWidths=[75*mm, 75*mm])
        photo_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        current_page_evidences.append(photo_table)
        # Espacio de 1 cm después de las fotos
        current_page_evidences.append(Spacer(1, 10*mm))
    else:
        # Si hay 1 sola foto, centrarla
        for img in photo_data:
            current_page_evidences.append(img)
            current_page_evidences.append(Spacer(1, 10*mm))
        
        if (idx + 1) % evidences_per_page == 0 or idx == len(evidences) - 1:
            story.extend(current_page_evidences)
            current_page_evidences = []
            
            if idx < len(evidences) - 1:
                story.append(PageBreak())
    
    def add_header_footer(canvas, doc):
        canvas.saveState()
        
        header_y = A4[1] - 15*mm
        
        canvas.setStrokeColor(black)
        canvas.setLineWidth(1)
        canvas.line(15*mm, header_y + 8*mm, A4[0] - 15*mm, header_y + 8*mm)
        
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(15*mm, header_y + 4*mm, "SOLUCIONES INTEGRALES - PAQUETE 1")
        canvas.setFont('Helvetica', 8)
        canvas.drawString(15*mm, header_y, "QUEBRADAS SAN IDELFONSO Y SAN CARLOS")
        
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawCentredString(A4[0]/2, header_y + 4*mm, "CONSORCIO BESALCO STRACON")
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(A4[0]/2, header_y, "(SEGURIDAD PATRIMONIAL)")
        
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(A4[0] - 15*mm, header_y + 4*mm, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
        
        # ✅ CORRECCIÓN: Usar solo doc.page (pageCount no existe durante el renderizado)
        canvas.drawRightString(A4[0] - 15*mm, header_y, f"Página {doc.page}")
        
        canvas.line(15*mm, header_y - 2*mm, A4[0] - 15*mm, header_y - 2*mm)
        
        canvas.setFont('Helvetica-Bold', 12)
        canvas.drawCentredString(A4[0]/2, header_y - 8*mm, title)
        
        canvas.line(15*mm, header_y - 10*mm, A4[0] - 15*mm, header_y - 10*mm)
        
        footer_y = 12*mm
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(HexColor('#666666'))
        canvas.drawCentredString(A4[0]/2, footer_y, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} - Sistema de Evidencia de Patrullas")
        
        canvas.restoreState()
    
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    
    buffer.seek(0)
    return buffer