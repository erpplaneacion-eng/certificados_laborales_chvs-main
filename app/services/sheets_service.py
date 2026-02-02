from typing import Optional, Dict, List
import re
import difflib
import unicodedata
from app.google_clients import get_gspread_client
from app.config import settings

def get_records_by_cedula(cedula: str) -> List[Dict]:
    """Obtiene TODOS los registros de contratos para una cédula específica"""
    gc = get_gspread_client()
    sh = gc.open_by_key(settings.SHEET_ID)
    ws = sh.worksheet("bd_contratacion")
    rows = ws.get_all_records()
    
    matching_records = []
    for row in rows:
        if str(row.get("cedula", "")).strip() == str(cedula).strip():
            matching_records.append(row)
    
    return matching_records

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