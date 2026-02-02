import os
from io import BytesIO
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Image

# --- FUNCIÓN DE DIBUJO ESTÁTICO (MINIMALISTA) ---
def draw_static_elements(canvas, doc):
    canvas.saveState()
    width, height = LETTER
    
    # --- DIBUJO DE NÚMERO DE PÁGINA (EXISTENTE) ---
    canvas.setFont("Helvetica", 9)
    page_num = f"Página {doc.page}"
    canvas.drawRightString(width - inch, 0.75 * inch, page_num)
    
    # --- INICIO DE CÓDIGO NUEVO PARA EL PIE DE PÁGINA ---
    # Define el texto y el estilo para el pie de página
    footer_text1 = "Calle 15 # 26-101 BODEGA 34 COMPLEJO INDUSTRIAL Y COMERCIAL CIC 1"
    footer_text2 = "YUMBO-VALLE"
    
    # Configura la fuente y el tamaño
    canvas.setFont("Helvetica", 9)
    
    # Dibuja las dos líneas de texto centradas en la parte inferior de la página
    # La coordenada Y se calcula desde el borde inferior
    canvas.drawCentredString(width / 2.0, 0.60 * inch, footer_text1)
    canvas.drawCentredString(width / 2.0, 0.45 * inch, footer_text2)
    # --- FIN DE CÓDIGO NUEVO ---
    
    canvas.restoreState()

def generar_certificado_en_memoria(datos: dict) -> BytesIO:
    buf = BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=LETTER,
        topMargin=inch,
        bottomMargin=inch,
        leftMargin=inch,
        rightMargin=inch
    )
    doc.datos = datos
    content_frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='content')
    page_template = PageTemplate(id='main_template', frames=[content_frame], onPage=draw_static_elements)
    doc.addPageTemplates([page_template])

    # === DEFINICIÓN DE ESTILOS PROFESIONALES ===
    styles = getSampleStyleSheet()
    style_body = ParagraphStyle('Body', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=12, leading=18, spaceAfter=12)
    style_periods = ParagraphStyle('Periods', parent=style_body, leftIndent=0.3*inch, fontSize=12)
    style_header = ParagraphStyle('Header', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, spaceAfter=6, fontName='Helvetica-Bold')
    style_signature = ParagraphStyle('Signature', parent=styles['Normal'], fontSize=12, alignment=TA_LEFT, spaceAfter=6, fontName='Helvetica-Bold', spaceBefore=0)
    style_contact = ParagraphStyle('Contact', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, spaceAfter=3)
    style_address = ParagraphStyle('Address', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, spaceAfter=3)

    story = []
    if datos.get("extra_top_margin", False):
        story.append(Spacer(1, 1.50 * inch))

    story.append(Paragraph(datos.get("nombre_empresa", "").upper(), ParagraphStyle(name='CompName', parent=style_header, fontSize=16)))
    story.append(Paragraph(datos.get("nit_empresa", ""), ParagraphStyle(name='CompNIT', parent=styles['Normal'], alignment=TA_CENTER, spaceAfter=24, fontSize=18)))
    story.append(Paragraph("<b>CERTIFICA QUE</b>", style_header))
    story.append(Spacer(1, 18))
    
    # Párrafo de introducción (sin cambios)
    intro_text = (
        f"El(la) Señor(a) <b>{datos['nombre']}</b> identificado(a) con Cédula de "
        f"Ciudadanía No <b>{datos['cedula']}</b> prestó sus servicios para esta empresa."
    )
    # Si hay periodos cerrados, se ajusta el texto de introducción
    if datos.get("periodos_cerrados_html"):
        intro_text = (
            f"El(la) Señor(a) <b>{datos['nombre']}</b> identificado(a) con Cédula de "
            f"Ciudadanía No <b>{datos['cedula']}</b> prestó sus servicios para esta empresa "
            f"en los siguientes periodos:"
        )
        story.append(Paragraph(intro_text, style_body))
        story.append(Paragraph(datos["periodos_cerrados_html"], style_periods))
    else:
         story.append(Paragraph(intro_text, style_body))

    # Párrafo para el periodo activo (si existe)
    if datos.get("periodo_activo_data"):
        activo_data = datos["periodo_activo_data"]
        
        # Construcción del párrafo para el periodo activo
        if datos.get("periodos_cerrados_html"):
            # Si hubo periodos cerrados, empieza con "Además,"
            texto_activo = (
                f"Además, desde el {activo_data['fecha_ingreso']} hasta la fecha se encuentra laborando en el cargo "
                f"de {activo_data['cargo']}."
            )
        else:
            # Si es el único periodo, es más directo
            texto_activo = (
                f"Actualmente y desde el {activo_data['fecha_ingreso']}, se encuentra laborando en el cargo "
                f"de {activo_data['cargo']}."
            )
        story.append(Paragraph(texto_activo, style_body))
    
    # --- AJUSTE DE LÓGICA PARA EL TIPO DE CONTRATO ---
    # Este párrafo ahora se muestra siempre, con una redacción adaptada.
    contrato_seleccionado = datos.get('tipo_contrato', 'de Obra o Labor')
    
    if datos.get("periodo_activo_data"):
        # Redacción para empleados activos
        texto_contrato = f"Mediante contrato <b>{contrato_seleccionado}</b> {datos['texto_adicional']}"
    else:
        # Redacción para ex-empleados, refiriéndose a su último contrato
        texto_contrato = f"Mediante contrato <b>{contrato_seleccionado}</b> {datos['texto_adicional']}"
        
    story.append(Paragraph(texto_contrato, style_body))
    
    # condición interna para cambiar el texto del salario.
    if datos.get("salario_num"):
        # Lista de cargos que usan la redacción de "ingreso promedio"
        cargos_con_ingreso_promedio = ["MANIPULADORA ALIMENTOS", "MANIPULADORA"]
        
        # El cargo se obtiene de los datos que vienen de main.py
        cargo_actual = datos.get("cargo")
        
        if cargo_actual in cargos_con_ingreso_promedio:
            # Texto modificado para el cargo de MANIPULADORA
            salario_text = (
                f"Con un ingreso mensual promedio de <b>{datos['salario_num']}</b> "
                f"(<b>{datos['salario_letras']}</b>) m/cte."
            )
        else:
            # Texto estándar para todos los demás cargos
            salario_text = (
                f"Con un salario básico mensual de <b>{datos['salario_num']}</b> "
                f"(<b>{datos['salario_letras']}</b>)."
            )
        
        story.append(Paragraph(salario_text, style_body))           

    cierre_text = (
        f"Para constancia de lo anterior se firma en Yumbo a los "
        f"{datos['dias_texto']} ({datos['dias_numero']}) días del mes de "
        f"{datos['mes']} de {datos['año']}."
    )
    story.append(Paragraph(cierre_text, style_body))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Cordialmente,", style_body))
    story.append(Spacer(1, 12))

    # --- INICIO DEL BLOQUE MODIFICADO ---
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        firma_path = os.path.join(base_dir, 'firma', 'firma.png')

        if os.path.exists(firma_path):
            # --- LÍNEA CORREGIDA ---
            # Se quita el argumento 'preserveAspectRatio' y 'height'.
            # Al dar solo el ancho, la altura se ajusta automáticamente manteniendo la proporción.
            firma_img = Image(firma_path, width=3.2*inch, height=0.7*inch)  # Ajusta el tamaño según sea necesario
            firma_img.hAlign = 'LEFT'
            story.append(firma_img)
        else:
            story.append(Paragraph("_______________________________", style_signature))
            
    except Exception as e:
        # Imprime el error en la consola para futura depuración
        print(f"Error al cargar la imagen de la firma: {e}")
        story.append(Paragraph("_______________________________", style_signature))
    # --- FIN DEL BLOQUE MODIFICADO ---
    
    story.append(Paragraph("<b>LUISA FERNANDA ORTIZ ERAZO</b>", style_signature))
    story.append(Paragraph("Departamento Gestión Humana", style_contact))
    story.append(Paragraph("Celular: 316 421 95 23", style_contact))
    story.append(Paragraph("Yumbo - Valle del Cauca", style_contact))
    story.append(Spacer(1, 12))

    doc.build(story)
    buf.seek(0)
    return buf