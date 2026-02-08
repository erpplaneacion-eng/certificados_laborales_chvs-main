from typing import Optional, Dict, List
import re
import difflib
import unicodedata
from datetime import datetime, timedelta
from app.google_clients import get_gspread_client
from app.config import settings

# --- CACHE GLOBAL ---
_CONTRACTS_CACHE: Optional[List[Dict]] = None
_LAST_CACHE_UPDATE: Optional[datetime] = None
CACHE_TTL_MINUTES = 15

def _get_cached_contracts(force_refresh: bool = False) -> List[Dict]:
    """
    Obtiene los contratos desde la caché o los descarga de Google Sheets si es necesario.
    """
    global _CONTRACTS_CACHE, _LAST_CACHE_UPDATE
    
    now = datetime.now()
    
    # Si no hay caché, o forzamos refresco, o el TTL expiró
    if (
        _CONTRACTS_CACHE is None 
        or force_refresh 
        or (_LAST_CACHE_UPDATE and (now - _LAST_CACHE_UPDATE) > timedelta(minutes=CACHE_TTL_MINUTES))
    ):
        print("Refrescando caché de contratos desde Google Sheets...")
        try:
            gc = get_gspread_client()
            sh = gc.open_by_key(settings.SHEET_ID)
            ws = sh.worksheet("bd_contratacion")
            _CONTRACTS_CACHE = ws.get_all_records()
            _LAST_CACHE_UPDATE = now
            print(f"Caché actualizada con {len(_CONTRACTS_CACHE)} registros.")
        except Exception as e:
            print(f"Error al actualizar caché: {e}")
            # Si falla y tenemos caché vieja, la devolvemos como fallback
            if _CONTRACTS_CACHE is None:
                raise e
                
    return _CONTRACTS_CACHE

def get_records_by_cedula(cedula: str) -> List[Dict]:
    """Obtiene TODOS los registros de contratos para una cédula específica usando caché"""
    rows = _get_cached_contracts()
    
    matching_records = []
    cedula_str = str(cedula).strip()
    
    for row in rows:
        # Convertir a string y limpiar ambos lados para comparación segura
        if str(row.get("cedula", "")).strip() == cedula_str:
            matching_records.append(row)
    
    return matching_records

def search_people(query: str) -> List[Dict[str, str]]:
    """
    Busca personas por nombre o cédula.
    Retorna lista única de {nombre, cedula}.
    """
    rows = _get_cached_contracts()
    query_norm = remove_accents(query).upper().strip()
    
    results = {} # Usar dict para unicidad por cédula
    
    for row in rows:
        nombre = str(row.get("Nombre del empleado", "")).strip()
        cedula = str(row.get("cedula", "")).strip()
        
        if not nombre or not cedula:
            continue
            
        nombre_norm = remove_accents(nombre).upper()
        
        # Coincidencia por cédula o nombre
        if query_norm in cedula or query_norm in nombre_norm:
            results[cedula] = {"nombre": nombre, "cedula": cedula}
            
            # Limitar a 20 resultados para no saturar la UI
            if len(results) >= 20:
                break
                
    return list(results.values())

def get_company_info_lookup() -> Dict[str, Dict[str, str]]:
    """
    Crea un diccionario de consulta avanzado para normalización de empresas.
    
    Returns:
        Dict[str, Dict[str, str]]: Diccionario donde cada alias mapea a:
            {
                "canonical_name": "Nombre oficial de la empresa",
                "nit": "NIT de la empresa"
            }
    
    Ejemplo:
        {
            "CORPORACION": {
                "canonical_name": "CORPORACION HACIA UN VALLE SOLIDARIO",
                "nit": "805.029.170-0"
            },
            "CORPORACION HACIA UN VALLE SOLIDARIO": {
                "canonical_name": "CORPORACION HACIA UN VALLE SOLIDARIO", 
                "nit": "805.029.170-0"
            }
        }
    """
    gc = get_gspread_client()
    sh = gc.open_by_key(settings.SHEET_ID)
    ws = sh.worksheet("Empresas")
    rows = ws.get_all_records()
    
    company_info_lookup = {}
    
    for row in rows:
        empresa_field = row.get("Empresa", "")
        nit = row.get("Nit", "")
        
        if empresa_field and nit:
            # Dividir por comas para obtener lista de alias
            aliases = [alias.strip() for alias in empresa_field.split(",")]
            
            if aliases:
                # El primer nombre en la lista es el nombre canónico (oficial)
                canonical_name = aliases[0]
                
                # Crear entrada para cada alias (incluido el canónico)
                for alias in aliases:
                    if alias:  # Solo agregar si no está vacío
                        company_info_lookup[alias] = {
                            "canonical_name": canonical_name,
                            "nit": nit
                        }
    
    return company_info_lookup

def remove_accents(input_str: str) -> str:
    """Elimina tildes y caracteres especiales del español."""
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def normalize_company_name(name: str) -> str:
    """
    Normaliza el nombre de la empresa expandiendo abreviaturas comunes,
    quitando tildes y estandarizando el formato.
    """
    if not name:
        return ""
    
    # Quitar tildes y convertir a mayúsculas
    norm = remove_accents(name).upper().strip()
    # Limpiar espacios extra
    norm = re.sub(r'\s+', ' ', norm)
    
    # Expansión de siglas (UT -> UNION TEMPORAL)
    norm = re.sub(r'\bUT\b', 'UNION TEMPORAL', norm)
    norm = re.sub(r'\bU\.T\.\b', 'UNION TEMPORAL', norm)
    norm = re.sub(r'\bU\.T\b', 'UNION TEMPORAL', norm)
    norm = re.sub(r'\bCS\b', 'CONSORCIO', norm)
    
    return norm

def find_best_company_match(raw_name: str, lookup_dict: Dict[str, Dict]) -> Optional[Dict]:
    """
    Intenta encontrar la mejor coincidencia para un nombre de empresa
    usando normalización, búsqueda difusa y validación de año.
    """
    if not raw_name:
        return None

    # 1. Intento Directo (Exacto)
    if raw_name in lookup_dict:
        return lookup_dict[raw_name]

    # Pre-procesar entrada
    normalized_input = normalize_company_name(raw_name)
    input_words = normalized_input.split()
    
    # Extraer año de la entrada
    input_year_match = re.search(r'\b(20\d{2}|19\d{2})\b', normalized_input)
    input_year = input_year_match.group(0) if input_year_match else None

    # 2. Intento Normalizado Exacto
    for key in lookup_dict:
        if normalize_company_name(key) == normalized_input:
            return lookup_dict[key]

    # 3. Búsqueda por coincidencia de palabras y validación de AÑO
    input_word_set = set(input_words)
    best_candidate = None
    max_overlap = 0
    
    for key, info in lookup_dict.items():
        key_norm = normalize_company_name(key)
        
        # Extraer año del candidato
        cand_year_match = re.search(r'\b(20\d{2}|19\d{2})\b', key_norm)
        cand_year = cand_year_match.group(0) if cand_year_match else None
        
        # REGLA DE ORO: Si ambos tienen año y son diferentes, NO es match
        if input_year and cand_year and input_year != cand_year:
            continue
            
        key_word_set = set(key_norm.split())
        
        # Intersección de palabras
        overlap_set = input_word_set.intersection(key_word_set)
        overlap_count = len(overlap_set)
        
        # Bono por año coincidente
        if input_year and cand_year and input_year == cand_year:
            overlap_count += 2

        # LÓGICA DE DECISIÓN:
        # Match si:
        # - Hay 3 o más palabras en común.
        # - O si TODAS las palabras que escribió el usuario están en el candidato 
        #   (ej: "CORPORACION" está dentro de "CORPORACION HACIA UN VALLE...")
        is_subset = overlap_count >= len(input_word_set) and len(input_word_set) > 0
        
        if (overlap_count > max_overlap) and (overlap_count >= 3 or is_subset):
            max_overlap = overlap_count
            best_candidate = info

    if best_candidate:
        return best_candidate

    # 4. Último recurso: Búsqueda difusa
    known_names = list(lookup_dict.keys())
    matches = difflib.get_close_matches(normalized_input, known_names, n=1, cutoff=0.7)
    if matches:
        match_norm = normalize_company_name(matches[0])
        match_year_match = re.search(r'\b(20\d{2}|19\d{2})\b', match_norm)
        match_year = match_year_match.group(0) if match_year_match else None
        if not (input_year and match_year and input_year != match_year):
            return lookup_dict[matches[0]]

    return None

# ============================================
# FUNCIONES PARA MANEJO DE SOLICITUDES
# ============================================

def actualizar_estado_solicitud(fila: int, estado: str = "Procesada"):
    """
    Actualiza el estado de una solicitud en la columna Q.

    Args:
        fila: Número de fila en la hoja (1-indexed)
        estado: Estado a marcar (default: "Procesada")
    """
    gc = get_gspread_client()
    sh = gc.open_by_key(settings.SOLICITUDES_SHEET_ID)
    ws = sh.worksheet("Solicitud Certificados")

    # Columna Q es la 17
    ws.update_cell(fila, 17, estado)

def registrar_historial(cedula: str, nombre_completo: str, url_carpeta: str, num_certificados: int):
    """
    Registra el procesamiento en la hoja Historial_Procesamiento.

    Args:
        cedula: Número de cédula
        nombre_completo: Nombre completo del empleado
        url_carpeta: URL de la carpeta en Drive
        num_certificados: Cantidad de certificados generados
    """
    from datetime import datetime

    gc = get_gspread_client()
    sh = gc.open_by_key(settings.SOLICITUDES_SHEET_ID)

    # Intentar obtener o crear la hoja Historial_Procesamiento
    try:
        ws = sh.worksheet("Historial_Procesamiento")
    except:
        # Si no existe, crearla con encabezados
        ws = sh.add_worksheet(title="Historial_Procesamiento", rows=1000, cols=5)
        ws.append_row(["Fecha Procesamiento", "Cédula", "Nombre Completo", "URL Carpeta Drive", "Certificados Generados"])

    # Agregar nueva fila
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ws.append_row([fecha_actual, cedula, nombre_completo, url_carpeta, num_certificados])

def obtener_solicitudes_recientes(limite: int = 20) -> List[Dict]:
    """
    Obtiene las solicitudes procesadas recientemente.

    Args:
        limite: Número máximo de resultados (default: 20)

    Returns:
        Lista de diccionarios con información de solicitudes procesadas
    """
    gc = get_gspread_client()
    sh = gc.open_by_key(settings.SOLICITUDES_SHEET_ID)

    try:
        ws = sh.worksheet("Historial_Procesamiento")
        records = ws.get_all_records()

        # Retornar los últimos N registros en orden inverso (más recientes primero)
        return list(reversed(records[-limite:]))
    except:
        # Si la hoja no existe aún, retornar lista vacía
        return []