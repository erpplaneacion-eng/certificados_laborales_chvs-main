from fastapi import FastAPI, Request, Form, HTTPException
# V-- NUEVA LÍNEA: Importar StaticFiles
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.services import sheets_service, drive_service
from app.services.template import generar_certificado_en_memoria
from datetime import datetime
from collections import defaultdict
from typing import Optional
import re
import locale
from num2words import num2words

# Configurar localización para español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, 'C')


app = FastAPI()

# --- BLOQUE AÑADIDO ---
# Monta la carpeta 'static' que está dentro de 'app' en la ruta URL '/static'
# Ahora el navegador puede acceder a los archivos pidiendo, por ejemplo, http://127.0.0.1:8000/static/mi_imagen.svg
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# --- FIN DEL BLOQUE AÑADIDO ---


templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    """Muestra el formulario para ingresar la cédula."""
    return templates.TemplateResponse("form.html", {"request": request})

# ... (el resto del archivo main.py permanece exactamente igual) ...
# (No es necesario que lo pegues aquí, solo asegúrate de que el resto del código siga ahí)

@app.post("/verificar-cedula")
def verificar_cedula(cedula: str = Form(...)):
    """
    Endpoint para verificar información preliminar de una cédula.
    Retorna último cargo y estado del contrato.
    """
    # Buscar todos los registros de la cédula
    records = sheets_service.get_records_by_cedula(cedula)
    if not records:
        raise HTTPException(status_code=404, detail=f"No se encontró ningún registro para la cédula {cedula}")
    
    # Ordenar por fecha de ingreso para identificar el contrato más reciente
    # Nota: Asumimos formato de fecha que se puede ordenar lexicográficamente
    sorted_records = sorted(records, key=lambda x: x.get("Fecha de Ingreso", ""), reverse=True)
    latest_record = sorted_records[0]
    
    # Extraer información del contrato más reciente
    ultimo_cargo = latest_record.get("Desc. Cargo", "No especificado")
    fecha_retiro = latest_record.get("Fecha de Retiro", "")
    
    # Determinar si el contrato está activo (Fecha de Retiro vacía)
    contrato_activo = not (fecha_retiro and str(fecha_retiro).strip())
    
    return JSONResponse(content={
        "ultimo_cargo": ultimo_cargo,
        "contrato_activo": contrato_activo
    })

def format_date_str(date_str: str) -> str:
    """
    Convierte una fecha en formato YYYYMMDD a formato legible en español.
    Ejemplo: "20240201" -> "01 de febrero de 2024"
    
    Args:
        date_str: Fecha en formato YYYYMMDD o cadena vacía
        
    Returns:
        Fecha formateada o "la actualidad" si está vacía
    """
    if not date_str or not str(date_str).strip():
        return "la actualidad"
    
    try:
        # Convertir string a datetime
        date_obj = datetime.strptime(str(date_str).strip(), "%Y%m%d")
        
        # Formatear con locale español configurado
        # Usar %d para día, %B para nombre completo del mes, %Y para año
        formatted = date_obj.strftime("%d de %B de %Y")
        
        # Remover ceros iniciales del día
        formatted = formatted.lstrip('0')
        if formatted.startswith('de'):
            formatted = '1' + formatted
            
        return formatted
    except (ValueError, TypeError):
        # Si no se puede parsear, retornar la fecha original
        return str(date_str) if date_str else "la actualidad"

def numero_a_letras(salario_str: str) -> str:
    """
    Convierte un salario en formato de cadena a su representación en letras.
    Ejemplo: "$2,400,000" -> "Dos millones cuatrocientos mil pesos"
    """
    try:
        # Limpiar la cadena de caracteres no numéricos
        numeros_solo = re.sub(r'[^\d]', '', salario_str)
        if not numeros_solo:
            return "Salario no válido"
        
        # Convertir a entero
        valor_numerico = int(numeros_solo)
        
        # Convertir a palabras en español
        texto_numerico = num2words(valor_numerico, lang='es')
        
        # Capitalizar primera letra y agregar "pesos"
        return f"{texto_numerico.capitalize()} pesos"
    except Exception:
        return "Salario no válido"

@app.post("/generar", response_class=HTMLResponse)
def generate_pdf_and_upload(cedula: str = Form(...), salario_manual: Optional[str] = Form(None),tipo_contrato: str = Form(...)):
    """
    Orquesta la generación y subida de múltiples certificados con lógica de negocio avanzada.
    1. Busca TODOS los registros por cédula en Google Sheets.
    2. Agrupa los contratos por empresa canónica.
    3. Genera un PDF por cada empresa con lógica condicional.
    4. Sube cada PDF a Google Drive.
    5. Devuelve enlaces a todos los archivos subidos.
    """
    # 1. Buscar TODOS los registros por cédula en Google Sheets
    records = sheets_service.get_records_by_cedula(cedula)
    if not records:
        raise HTTPException(status_code=404, detail=f"No se encontró ningún registro para la cédula {cedula}")

    # 2. Obtener diccionario de información de empresas para normalización
    company_info_lookup = sheets_service.get_company_info_lookup()

    # 3. Agrupar contratos por nombre canónico de empresa
    contracts_by_canonical_company = defaultdict(list)
    for record in records:
        # Obtener nombre crudo de la empresa desde bd_contratacion
        raw_company_name = record.get("Nombre de empresa", "Empresa No Especificada")
        
        # Buscar información normalizada de la empresa (usando Smart Matching)
        company_info = sheets_service.find_best_company_match(raw_company_name, company_info_lookup)
        
        if company_info:
            # Usar el nombre canónico para agrupación
            canonical_name = company_info["canonical_name"]
        else:
            # Fallback: usar el nombre crudo si no se encuentra en el lookup
            canonical_name = raw_company_name
        
        contracts_by_canonical_company[canonical_name].append(record)

    # 4. Generar certificados por empresa (usando nombres canónicos)
    generated_files = []
    now = datetime.now()
    
    for canonical_company_name, contracts in contracts_by_canonical_company.items():
        try:
            # Obtener nombre del empleado (usar el del primer contrato)
            nombre_completo = contracts[0].get("Nombre del empleado", "Desconocido")
            
            # Separar periodos activos de los cerrados
            periodos_cerrados = []
            periodo_activo = None
            
            # Ordenar contratos por fecha de ingreso para asegurar un historial cronológico
            sorted_contracts = sorted(contracts, key=lambda x: x.get("Fecha de Ingreso", ""))

            for contract in sorted_contracts:
                fecha_ingreso_raw = contract.get("Fecha de Ingreso", "")
                fecha_retiro_raw = contract.get("Fecha de Retiro", "")
                cargo_periodo = contract.get("Desc. Cargo", "No especificado")
                
                fecha_ingreso_formateada = format_date_str(fecha_ingreso_raw)
                
                if fecha_retiro_raw and str(fecha_retiro_raw).strip():
                    fecha_retiro_formateada = format_date_str(fecha_retiro_raw)
                    # --- CORRECCIÓN CLAVE ---
                    # Se asegura que el string del periodo cerrado incluya el cargo.
                    periodo = f"• Desde el {fecha_ingreso_formateada} hasta el {fecha_retiro_formateada} en el cargo de {cargo_periodo}"
                    if periodo not in periodos_cerrados:
                        periodos_cerrados.append(periodo)
                else:
                    # Este es el contrato activo
                    periodo_activo = {
                        'fecha_ingreso': fecha_ingreso_formateada,
                        'cargo': cargo_periodo
                    }
            
            # Usar el último contrato de la lista ordenada para determinar los detalles finales
            latest_contract = sorted_contracts[-1]
            cargo = latest_contract.get("Desc. Cargo", "No especificado")
            
            # Determinar si el último contrato está activo
            fecha_retiro_ultimo = latest_contract.get("Fecha de Retiro", "")
            contrato_activo = not (fecha_retiro_ultimo and str(fecha_retiro_ultimo).strip())
            
            # Implementar lógica de salario condicional
            salario_final_num = ""
            salario_final_letras = ""
            
            if contrato_activo:
                # Usar salario manual si fue proporcionado, sino usar el del sistema
                salario_a_usar = salario_manual if salario_manual else latest_contract.get("SALARIO BASICO", "")
                
                if salario_a_usar:
                    salario_final_num = salario_a_usar if '$' in str(salario_a_usar) else f"${salario_a_usar}"
                    salario_final_letras = numero_a_letras(salario_final_num)
            
            # Implementar lógica de texto dinámico
            cargos_pae = ["SUPERVISOR PROGRAMA", "MANIPULADORA ALIMENTOS", "COORDINADOR DE PROGRAMA", "MANIPULADORA"]
            
            # La lógica del texto PAE ahora depende solo del cargo, no del estado del contrato
            if cargo in cargos_pae:
                texto_adicional = "en el programa de alimentación escolar PAE."
            else:
                texto_adicional = "."
            
            # Buscar NIT de la empresa usando el nombre canónico
            company_info = company_info_lookup.get(canonical_company_name)
            if company_info:
                nit_empresa = company_info["nit"]
            else:
                # Fallback: buscar por cualquier contrato del grupo
                nit_empresa = "NIT no encontrado"
                for contract in contracts:
                    raw_name = contract.get("Nombre de empresa", "")
                    contract_info = company_info_lookup.get(raw_name)
                    if contract_info:
                        nit_empresa = contract_info["nit"]
                        break
            
            # Detectar si necesita margen superior extra para papel preimpreso
            extra_margin = canonical_company_name == "CORPORACION HACIA UN VALLE SOLIDARIO"
            
            # Preparar datos para la plantilla con nueva lógica de negocio
            datos_plantilla = {
                "nombre": nombre_completo,
                "cedula": cedula,
                "periodos_cerrados_html": "<br/>".join(periodos_cerrados) if periodos_cerrados else None,
                "periodo_activo_data": periodo_activo,
                "cargo": cargo,
                "salario_num": salario_final_num,
                "salario_letras": salario_final_letras,
                "texto_adicional": texto_adicional,
                "nombre_empresa": canonical_company_name,
                "nit_empresa": nit_empresa,
                "extra_top_margin": extra_margin,
                "tipo_contrato": tipo_contrato, # Pasamos el valor a la plantilla
                "dias_texto": num2words(now.day, lang='es'),
                "dias_numero": str(now.day),
                "mes": now.strftime("%B"),
                "año": str(now.year)
            }
            
            # Generar PDF en memoria
            pdf_bytes = generar_certificado_en_memoria(datos_plantilla)
            
            # Crear nombre de archivo descriptivo usando nombre canónico
            company_safe = canonical_company_name.replace(' ', '_').replace(',', '').replace('/', '_')
            pdf_filename = f"Certificado_{nombre_completo.replace(' ', '_')}_{company_safe}_{cedula}.pdf"
            
            # Subir a Google Drive
            file_info = drive_service.upload_pdf(pdf_bytes, pdf_filename)
            view_link = file_info.get("webViewLink")
            
            generated_files.append({
                "empresa": canonical_company_name,
                "filename": pdf_filename,
                "link": view_link
            })
            
        except Exception as e:
            # Si hay error con una empresa, continuar con las otras
            generated_files.append({
                "empresa": canonical_company_name,
                "filename": f"Error: {str(e)}",
                "link": None
            })

    # 5. Generar respuesta con todos los enlaces
    if not generated_files:
        raise HTTPException(status_code=500, detail="No se pudo generar ningún certificado")
    
    # --- INICIO DEL BLOQUE DE RESPUESTA HTML MEJORADO ---
    
    file_list_html = ""
    success_count = 0
    
    for file_info in generated_files:
        if file_info["link"]:
            success_count += 1
            file_list_html += f"""
                <li class="success">
                    <span class="icon">📄</span>
                    <div class="details">
                        <strong>{file_info["empresa"]}</strong>
                        <span>{file_info["filename"]}</span>
                    </div>
                    <a href="{file_info['link']}" target="_blank" class="download-link">Ver / Descargar</a>
                </li>
            """
        else:
            file_list_html += f"""
                <li class="error">
                    <span class="icon">❌</span>
                    <div class="details">
                        <strong>{file_info["empresa"]}</strong>
                        <span>{file_info["filename"]}</span>
                    </div>
                </li>
            """

    return HTMLResponse(content=f"""
        <!doctype html>
        <html>
            <head>
                <meta charset="utf-8">
                <title>Certificados Generados</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background-color: #f5f5f5;
                        margin: 0;
                        padding: 40px 20px;
                        display: flex;
                        justify-content: center;
                        align-items: flex-start;
                        min-height: 100vh;
                    }}
                    .container {{
                        background-color: white;
                        max-width: 700px;
                        width: 100%;
                        padding: 30px 40px;
                        border-radius: 10px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                        text-align: center;
                    }}
                    h1 {{
                        color: #4CAF50;
                        font-size: 28px;
                        margin-bottom: 10px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 10px;
                    }}
                    .summary {{
                        color: #555;
                        font-size: 18px;
                        margin-bottom: 30px;
                    }}
                    ul {{
                        list-style-type: none;
                        padding: 0;
                        margin: 0;
                    }}
                    li {{
                        display: flex;
                        align-items: center;
                        text-align: left;
                        padding: 15px;
                        margin-bottom: 15px;
                        border-radius: 8px;
                        border: 1px solid #ddd;
                        transition: box-shadow 0.2s;
                    }}
                    li:hover {{
                        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                    }}
                    li.success {{
                        border-left: 5px solid #4CAF50;
                    }}
                    li.error {{
                        border-left: 5px solid #d32f2f;
                        background-color: #ffebee;
                    }}
                    .icon {{
                        font-size: 24px;
                        margin-right: 15px;
                    }}
                    .details {{
                        display: flex;
                        flex-direction: column;
                        flex-grow: 1;
                    }}
                    .details strong {{
                        color: #333;
                        font-size: 16px;
                    }}
                    .details span {{
                        color: #777;
                        font-size: 13px;
                        word-break: break-all;
                    }}
                    .download-link {{
                        background-color: #e8f5e8;
                        color: #4CAF50;
                        padding: 8px 15px;
                        border-radius: 20px;
                        text-decoration: none;
                        font-weight: bold;
                        font-size: 14px;
                        white-space: nowrap;
                        transition: background-color 0.2s;
                    }}
                    .download-link:hover {{
                        background-color: #d1e7d2;
                    }}
                    .btn-back {{
                        display: inline-block;
                        margin-top: 30px;
                        background-color: #4CAF50;
                        color: white;
                        padding: 12px 30px;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                        font-size: 16px;
                        text-decoration: none;
                        transition: background-color 0.2s;
                    }}
                    .btn-back:hover {{
                        background-color: #45a049;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1><span class="icon-title">✅</span>Proceso Completado</h1>
                    <p class="summary">Se generaron <strong>{success_count}</strong> certificados con éxito.</p>
                    <ul>
                        {file_list_html}
                    </ul>
                    <a href="/" class="btn-back">Generar Otros Certificados</a>
                </div>
            </body>
        </html>
    """)
    # --- FIN DEL BLOQUE DE RESPUESTA HTML MEJORADO ---