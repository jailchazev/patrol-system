"""
Generador de PDF profesional para evidencias de patrullas.
Versión final con encabezado corporativo exacto.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
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
        topMargin=45*mm,
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
        
        # Dimensiones
        page_width = A4[0]
        left_margin = 15*mm
        right_margin = 15*mm
        available_width = page_width - left_margin - right_margin
        
        # ESTRUCTURA DE 5 COLUMNAS:
        # Logo | Texto Centro 1 | Texto Centro 2 | Label Fecha | Valor Fecha
        col_logo = 30*mm
        col_centro_1 = 50*mm
        col_centro_2 = 50*mm
        col_fecha_label = 20*mm
        col_fecha_valor = 30*mm
        
        # Fecha actual Perú
        peru_now = datetime.utcnow() - timedelta(hours=5)
        fecha_str = peru_now.strftime('%d/%m/%Y')
        total_pages = max(1, (len(evidences) + evidences_per_page - 1) // evidences_per_page)
        pagina_str = f"Página {doc.page} de {total_pages}"
        
        # Estilos
        estilo_titulo = ParagraphStyle('EstiloTitulo', fontSize=8, leading=10, alignment=TA_CENTER, fontName='Helvetica-Bold')
        estilo_subtitulo = ParagraphStyle('EstiloSubtitulo', fontSize=7, leading=9, alignment=TA_CENTER, fontName='Helvetica')
        estilo_titulo_grande = ParagraphStyle('EstiloTituloGrande', fontSize=10, leading=12, alignment=TA_CENTER, fontName='Helvetica-Bold')
        estilo_texto = ParagraphStyle('EstiloTexto', fontSize=8, alignment=TA_LEFT, fontName='Helvetica')
        estilo_texto_center = ParagraphStyle('EstiloTextoCenter', fontSize=8, alignment=TA_CENTER, fontName='Helvetica')
        
        # Logo (texto o imagen)
        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'logo.png')
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=28*mm, height=10*mm)
            except:
                logo = Paragraph("<b>BESALCO | STRACON</b>", estilo_titulo)
        else:
            logo = Paragraph("<b>BESALCO | STRACON</b>", estilo_titulo)
        
        # ESTRUCTURA DE 5 COLUMNAS x 3 FILAS
        header_data = [
            # Fila 0: Logo | Texto superior (colspan 2) | "Fecha:" | Valor fecha
            [logo, 
             Paragraph("SOLUCIONES INTEGRALES - PAQUETE 1<br/>QUEBRADAS SAN IDELFONSO Y SAN CARLOS", estilo_titulo),
             '',  # placeholder para colspan
             Paragraph("Fecha:", estilo_texto),
             Paragraph(fecha_str, estilo_texto_center)],
            
            # Fila 1: Logo continúa | Texto medio (colspan 2) | Fecha continúa | Valor continúa
            ['',
             Paragraph("CONSORCIO BESALCO STRACON<br/>(SEGURIDAD PATRIMONIAL)", estilo_subtitulo),
             '',
             '',
             ''],
            
            # Fila 2: Logo continúa | Título (colspan 2) | Página (colspan 2)
            ['',
             Paragraph(title, estilo_titulo_grande),
             '',
             Paragraph(pagina_str, estilo_texto_center),
             '']
        ]
        
        # Crear tabla
        header_table = Table(
            header_data, 
            colWidths=[col_logo, col_centro_1, col_centro_2, col_fecha_label, col_fecha_valor],
            rowHeights=[12*mm, 10*mm, 10*mm]
        )
        
        # Aplicar estilos con SPANS CORRECTOS
        header_table.setStyle(TableStyle([
            # Bordes de todas las celdas
            ('GRID', (0, 0), (-1, -1), 0.5, black),
            
            # SPAN DEL LOGO: Columna 0, Filas 0-2
            ('SPAN', (0, 0), (0, 2)),
            
            # SPAN TEXTO FILA 0: Columnas 1-2, Fila 0
            ('SPAN', (1, 0), (2, 0)),
            
            # SPAN TEXTO FILA 1: Columnas 1-2, Fila 1
            ('SPAN', (1, 1), (2, 1)),
            
            # SPAN FECHA LABEL: Columna 3, Filas 0-1
            ('SPAN', (3, 0), (3, 1)),
            
            # SPAN FECHA VALOR: Columna 4, Filas 0-1
            ('SPAN', (4, 0), (4, 1)),
            
            # SPAN TÍTULO FILA 2: Columnas 1-2, Fila 2
            ('SPAN', (1, 2), (2, 2)),
            
            # SPAN PÁGINA FILA 2: Columnas 3-4, Fila 2
            ('SPAN', (3, 2), (4, 2)),
            
            # Alineación vertical
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alineación horizontal
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),    # Logo centrado
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),    # Texto central centrado
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),     # Label "Fecha:" alineado derecha
            ('ALIGN', (4, 0), (4, -1), 'CENTER'),    # Valor fecha centrado
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        # Posicionar encabezado
        header_y = A4[1] - 42*mm
        header_table.wrapOn(canvas, available_width, 32*mm)
        header_table.drawOn(canvas, left_margin, header_y)
        
        # Pie de página
        footer_y = 12*mm
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(HexColor('#666666'))
        canvas.drawCentredString(A4[0]/2, footer_y, f"Generado el {peru_now.strftime('%d/%m/%Y %H:%M')} - Sistema de Evidencia de Patrullas")
        
        canvas.restoreState()
    
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    
    buffer.seek(0)
    return buffer