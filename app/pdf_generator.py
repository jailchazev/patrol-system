"""
Generador de PDF profesional para evidencias de patrullas.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from io import BytesIO
from datetime import datetime, timedelta
import base64
import os


def generate_evidence_pdf(evidences, title="REPORTE SEMANAL"):
    """Genera PDF con encabezado corporativo tipo tabla."""
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=45*mm,  # Aumentado para dejar espacio al encabezado
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
                dt = dt - timedelta(hours=5)
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
                    img = Image(photo_buffer, width=70*mm, height=47*mm)
                    photo_data.append(img)
                except Exception as e:
                    print(f"Error procesando foto: {e}")
                    continue
            
            if photo_data:
                if len(photo_data) == 2:
                    spacer_column = Spacer(10*mm, 47*mm)
                    photo_table = Table([[photo_data[0], spacer_column, photo_data[1]]])
                    photo_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    current_page_evidences.append(photo_table)
                else:
                    current_page_evidences.append(photo_data[0])
                
                current_page_evidences.append(Spacer(1, 5*mm))
        
        if (idx + 1) % evidences_per_page == 0 or idx == len(evidences) - 1:
            story.extend(current_page_evidences)
            current_page_evidences = []
            
            if idx < len(evidences) - 1:
                story.append(PageBreak())
    
    def add_header_footer(canvas, doc):
        canvas.saveState()
        
        # ========== ENCABEZADO TIPO TABLA ==========
        # Ancho total disponible
        page_width = A4[0]
        left_margin = 15*mm
        right_margin = 15*mm
        available_width = page_width - left_margin - right_margin
        
        # Anchos de columnas: Logo | Texto central | Fecha/Página
        col_logo = 35*mm
        col_fecha = 35*mm
        col_centro = available_width - col_logo - col_fecha
        
        # Obtener fecha actual en Perú
        peru_now = datetime.utcnow() - timedelta(hours=5)
        fecha_str = peru_now.strftime('%d/%m/%Y')
        pagina_str = f"Página {doc.page}"
        
        # Estilos de texto para el encabezado
        estilo_titulo = ParagraphStyle('EstiloTitulo', fontSize=8, leading=10, alignment=TA_CENTER, fontName='Helvetica-Bold')
        estilo_subtitulo = ParagraphStyle('EstiloSubtitulo', fontSize=7, leading=9, alignment=TA_CENTER, fontName='Helvetica')
        estilo_titulo_grande = ParagraphStyle('EstiloTituloGrande', fontSize=10, leading=12, alignment=TA_CENTER, fontName='Helvetica-Bold')
        estilo_fecha = ParagraphStyle('EstiloFecha', fontSize=8, alignment=TA_LEFT, fontName='Helvetica')
        estilo_fecha_valor = ParagraphStyle('EstiloFechaValor', fontSize=8, alignment=TA_LEFT, fontName='Helvetica')
        estilo_pagina = ParagraphStyle('EstiloPagina', fontSize=8, alignment=TA_LEFT, fontName='Helvetica')
        
        # Intentar cargar el logo
        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'logo.png')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=30*mm, height=12*mm)
        else:
            logo = Paragraph("<b>BESALCO | STRACON</b>", estilo_titulo)
        
        # Estructura de la tabla: 3 filas x 3 columnas
        # Fila 0: Logo | SOLUCIONES INTEGRALES... | Fecha:
        # Fila 1: (logo span) | CONSORCIO BESALCO... | 03/09/2026
        # Fila 2: (logo span) | REPORTE SEMANAL | Página 1
        
        header_data = [
            [logo, 
             Paragraph("SOLUCIONES INTEGRALES - PAQUETE 1<br/>QUEBRADAS SAN IDELFONSO Y SAN CARLOS", estilo_titulo),
             Paragraph("Fecha:", estilo_fecha)],
            ['',
             Paragraph("CONSORCIO BESALCO STRACON<br/>(SEGURIDAD PATRIMONIAL)", estilo_subtitulo),
             Paragraph(fecha_str, estilo_fecha_valor)],
            ['',
             Paragraph(title, estilo_titulo_grande),
             Paragraph(pagina_str, estilo_pagina)]
        ]
        
        # Crear tabla
        header_table = Table(header_data, colWidths=[col_logo, col_centro, col_fecha], rowHeights=[12*mm, 10*mm, 10*mm])
        header_table.setStyle(TableStyle([
            # Bordes de todas las celdas
            ('GRID', (0, 0), (-1, -1), 0.5, black),
            # Fusionar logo verticalmente (filas 0-2, columna 0)
            ('SPAN', (0, 0), (0, 2)),
            # Fusionar fecha verticalmente (filas 0-1, columna 2)
            ('SPAN', (2, 0), (2, 1)),
            # Alineación vertical centrada
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Alineación horizontal
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Logo centrado
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Texto central centrado
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),    # Fecha alineada a la izquierda
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        # Posición del encabezado (desde arriba de la página)
        header_y = A4[1] - 42*mm  # Ajustado para que no se superponga con el contenido
        
        # Dibujar la tabla del encabezado
        header_table.wrapOn(canvas, available_width, 32*mm)
        header_table.drawOn(canvas, left_margin, header_y)
        
        # ========== PIE DE PÁGINA ==========
        footer_y = 12*mm
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(HexColor('#666666'))
        canvas.drawCentredString(A4[0]/2, footer_y, f"Generado el {peru_now.strftime('%d/%m/%Y %H:%M')} - Sistema de Evidencia de Patrullas")
        
        canvas.restoreState()
    
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    
    buffer.seek(0)
    return buffer