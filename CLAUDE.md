# Certificados Laborales CHVS - Documentación para Claude Code

## 🚀 Comandos de Desarrollo

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar en desarrollo (puerto 8000)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ejecutar en producción
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 📁 Estructura del Proyecto

```
app/
├── main.py                      # FastAPI app principal con endpoints
├── config.py                    # Configuración y variables de entorno
├── google_clients.py            # Clientes de Google (Drive, Sheets)
├── services/
│   ├── drive_service.py         # Manejo de Google Drive
│   ├── sheets_service.py        # Manejo de Google Sheets + Caché
│   └── template.py              # Generación de PDFs con ReportLab
├── templates/
│   └── form.html                # Frontend HTML
└── static/
    ├── styles.css               # Estilos CSS con Glassmorphism
    ├── script.js                # JavaScript para búsqueda y solicitudes
    └── PROYECTO CERTIFICADO LABORAL CHVS.svg
```

## 🏗️ Arquitectura del Sistema

### Capa 1: Presentación (Frontend)
- **form.html**: Interfaz web con búsqueda de empleados y visualización de solicitudes procesadas
- **script.js**:
  - Búsqueda en tiempo real con debounce (300ms)
  - Carga de solicitudes recientes cada 30 segundos
  - Verificación de cédula dinámica
- **styles.css**: Diseño moderno con efectos glassmorphism polimórficos

### Capa 2: Lógica de Negocio (FastAPI)
- **main.py**: Endpoints REST
  - `GET /` - Renderiza formulario
  - `POST /verificar-cedula` - Valida empleado
  - `GET /search` - Búsqueda de empleados
  - `POST /generar` - Genera certificados manualmente
  - `POST /procesar-solicitud` - Procesa solicitud automática desde Google Form
  - `GET /solicitudes-recientes` - Obtiene últimas 20 solicitudes procesadas
- **template.py**: Genera PDFs con logos, tablas y campos condicionales

### Capa 3: Datos (Google Workspace)
- **Google Sheets**: Base de datos principal
  - `bd_contratacion` - Contratos de empleados (SHEET_ID)
  - `Empresas` - Normalización de nombres de empresas
  - `Solicitud Certificados` - Formulario de solicitudes (SOLICITUDES_SHEET_ID)
  - `Historial_Procesamiento` - Log de certificados generados
- **Google Drive**: Almacenamiento de PDFs en Shared Drive

## 🔄 Sistema de Solicitudes Automáticas

### Flujo Completo:
1. **Usuario llena Google Form** → Datos van a hoja "Solicitud Certificados"
2. **Google Apps Script Trigger** detecta nueva fila y llama a `/procesar-solicitud`
3. **FastAPI app** genera PDFs y los sube a Drive
4. **App retorna JSON** con URL de carpeta y cantidad de certificados
5. **Google Apps Script** actualiza:
   - Columna Q de "Solicitud Certificados" → "Procesada"
   - Agrega fila en "Historial_Procesamiento"
6. **Frontend** muestra solicitudes recientes automáticamente

### Google Apps Script (Trigger):
```javascript
function onFormSubmit(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Solicitud Certificados");
  var lastRow = sheet.getLastRow();
  var cedula = sheet.getRange(lastRow, 3).getValue();
  var estado = sheet.getRange(lastRow, 17).getValue();

  if (estado === "" || estado === null) {
    var url = "https://certificadoslaboraleschvs-main-production.up.railway.app/procesar-solicitud";
    var payload = {"cedula": String(cedula), "fila": lastRow};
    var options = {"method": "post", "payload": payload, "muteHttpExceptions": true};

    try {
      var response = UrlFetchApp.fetch(url, options);
      var responseCode = response.getResponseCode();

      if (responseCode === 200) {
        var jsonResponse = JSON.parse(response.getContentText());
        sheet.getRange(lastRow, 17).setValue("Procesada");

        var historialSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Historial_Procesamiento");
        if (historialSheet) {
          var fechaActual = Utilities.formatDate(new Date(), "GMT-5", "dd/MM/yyyy HH:mm:ss");
          historialSheet.appendRow([fechaActual, jsonResponse.cedula, jsonResponse.nombre, jsonResponse.folder_url, jsonResponse.certificados_generados]);
        }
      } else {
        sheet.getRange(lastRow, 17).setValue("Error HTTP " + responseCode);
      }
    } catch (error) {
      sheet.getRange(lastRow, 17).setValue("Error: " + error.toString().substring(0, 50));
    }
  }
}
```

**IMPORTANTE**: La app NO escribe directamente en Google Sheets. Solo genera PDFs y retorna JSON. Google Apps Script tiene los permisos para escribir en Sheets.

## 📊 Sistema de Caché Global (sheets_service.py)

```python
_CONTRACTS_CACHE: Optional[List[Dict]] = None
_LAST_CACHE_UPDATE: Optional[datetime] = None
CACHE_TTL_MINUTES = 15  # Tiempo de vida: 15 minutos
```

### Funciones con Caché:
- `_get_cached_contracts()` - Descarga contratos solo si caché expiró
- `get_records_by_cedula(cedula)` - Obtiene contratos de un empleado
- `search_people(query)` - Busca por nombre o cédula (máx. 20 resultados)

**Ventaja**: Reduce llamadas a Google Sheets API y mejora velocidad de búsqueda.

## 🏢 Sistema de Normalización de Empresas

### Problema:
Los nombres de empresas en contratos tienen variaciones:
- "CORPORACION"
- "CORPORACION HACIA UN VALLE SOLIDARIO"
- "UT NUEVA COLOMBIA 2023"
- "UNION TEMPORAL NUEVA COLOMBIA 2023"

### Solución:
Hoja "Empresas" con aliases:
```
Empresa                                           | Nit
CORPORACION HACIA UN VALLE SOLIDARIO, CORPORACION | 805.029.170-0
UNION TEMPORAL NUEVA COLOMBIA 2023, UT NC 2023    | 900.XXX.XXX-X
```

### Algoritmo (sheets_service.py):
```python
def find_best_company_match(raw_name, lookup_dict):
    # 1. Intento exacto
    # 2. Normalización (quita tildes, expande "UT" → "UNION TEMPORAL")
    # 3. Coincidencia por palabras + validación de año
    # 4. Búsqueda difusa (difflib con cutoff=0.7)
```

### Reglas Críticas:
- ✅ Si ambos tienen año y coinciden → BONUS +2 palabras
- ❌ Si ambos tienen año y NO coinciden → DESCARTA candidato
- ✅ Match si: 3+ palabras en común O todas las palabras input están en candidato

**Uso en template.py (línea ~120-150)**:
```python
company_lookup = sheets_service.get_company_info_lookup()
match_info = sheets_service.find_best_company_match(empresa_contrato, company_lookup)
if match_info:
    empresa_normalizada = match_info["canonical_name"]
    nit = match_info["nit"]
```

## 📄 Lógica de Renderizado Condicional (template.py)

### Tipos de Certificados:
1. **Certificado con Salarios** (si contrato activo)
2. **Certificado sin Salarios** (si contrato finalizado)
3. **Carta de Recomendación** (solo si contrato finalizado)

### Campos Condicionales:

#### Salario Manual (template.py línea ~85):
```python
# Solo para cargos específicos con contrato activo
CARGOS_CON_SALARIO_MANUAL = ['MANIPULADORA ALIMENTOS', 'MANIPULADORA']

if ultimo_cargo in CARGOS_CON_SALARIO_MANUAL and contrato_activo:
    # Mostrar campo de salario manual en form.html
    # Si usuario ingresa salario → usar ese
    # Si no → usar salario del sistema
```

#### Texto de Estado Laboral (template.py línea ~250):
```python
if contrato_activo:
    texto = "se desempeña actualmente como"
else:
    texto = "se desempeñó como"
```

#### Carta de Recomendación (main.py línea ~380):
```python
if not contrato_activo:
    # Generar carta_recomendacion.pdf
    carta_pdf = template_service.generar_carta_recomendacion(...)
```

## 📂 Organización en Google Drive

### Estructura:
```
DRIVE_FOLDER_ID (Shared Drive)
├── NombreCompleto_Cedula/
│   ├── certificado_con_salarios.pdf
│   ├── certificado_sin_salarios.pdf
│   └── carta_recomendacion.pdf (si aplica)
├── OtraPersona_987654321/
│   └── ...
```

### Función (drive_service.py línea 21-62):
```python
def get_or_create_person_folder(nombre_completo: str, cedula: str) -> str:
    # 1. Busca carpeta existente: "NombreCompleto_Cedula"
    # 2. Si no existe, la crea
    # 3. Retorna folder_id
```

**IMPORTANTE**: Usar Shared Drives, NO "Mi unidad". Service accounts no tienen acceso a "Mi unidad".

## 🎨 Frontend con Glassmorphism

### Características del Diseño:
- **Efecto de vidrio translúcido**: `backdrop-filter: blur(10px)`
- **Gradientes sutiles**: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- **Animaciones suaves**:
  - Entrada: `slideInUp` (0.6s)
  - Hover: elevación y desplazamiento
  - Icono robot: `pulse` infinito
- **Scrollbar personalizado** con gradiente púrpura
- **Tarjetas con sombras dinámicas**

### Layout:
1. Título principal
2. Buscador de empleados
3. Formulario de cédula y tipo de contrato
4. Botón "Generar Certificados"
5. **Tarjeta del asistente** (debajo del botón) con solicitudes recientes

## 🔑 Variables de Entorno Requeridas

```env
GOOGLE_CREDENTIALS_JSON={"type": "service_account", ...}
SHEET_ID=1abcdefghijklmnopqrstuvwxyz1234567890
SOLICITUDES_SHEET_ID=1OXIJ5CllTUhaCeWJXC6XM8VKD1-ahtPgvD6zwCX0x_w
DRIVE_FOLDER_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ
PORT=8000
```

### Permisos Necesarios:
- **Service Account** debe tener acceso de Editor en:
  - Shared Drive (DRIVE_FOLDER_ID)
  - Google Sheet de contratos (SHEET_ID)
  - ⚠️ NO necesita acceso a SOLICITUDES_SHEET_ID (Apps Script escribe)

## 📍 Archivos Críticos y Líneas Importantes

### main.py
- **Línea 28-45**: Endpoint `/` - Renderiza formulario
- **Línea 50-95**: Endpoint `/verificar-cedula` - Valida empleado y retorna cargo
- **Línea 100-135**: Endpoint `/search` - Búsqueda con caché
- **Línea 140-400**: Endpoint `/generar` - Generación manual de certificados
- **Línea 466-620**: Endpoint `/procesar-solicitud` - Procesamiento automático
  - ⚠️ **Línea 600-620**: NO escribe en Sheets, solo retorna JSON
- **Línea 622-632**: Endpoint `/solicitudes-recientes` - Lista últimas 20

### sheets_service.py
- **Línea 10-42**: Sistema de caché global
- **Línea 44-56**: `get_records_by_cedula()` - Obtiene contratos por cédula
- **Línea 58-85**: `search_people()` - Búsqueda con normalización
- **Línea 87-137**: `get_company_info_lookup()` - Carga empresas y aliases
- **Línea 167-242**: `find_best_company_match()` - Algoritmo de normalización
- **Línea 248-261**: `actualizar_estado_solicitud()` - Marca como "Procesada"
- **Línea 263-288**: `registrar_historial()` - Log de procesamiento
- **Línea 290-311**: `obtener_solicitudes_recientes()` - Últimas 20 solicitudes

### template.py
- **Línea 25-85**: `generar_certificado()` - Lógica principal de generación
- **Línea 120-150**: Normalización de empresa con lookup
- **Línea 180-220**: Construcción de tabla de contratos
- **Línea 250-280**: Texto condicional según estado laboral
- **Línea 350-420**: `generar_carta_recomendacion()` - Carta solo para finalizados

### drive_service.py
- **Línea 21-62**: `get_or_create_person_folder()` - Carpetas por persona
- **Línea 64-100**: `upload_pdf()` - Sube PDF a carpeta específica
- **Línea 102-130**: `get_folder_url()` - Genera URL pública de carpeta

### form.html
- **Línea 14-25**: Buscador de empleados
- **Línea 35-77**: Formulario principal
- **Línea 79-88**: Tarjeta del asistente con solicitudes recientes

### script.js
- **Línea 4-35**: Búsqueda con debounce (300ms)
- **Línea 37-48**: `performSearch()` - Llamada a `/search`
- **Línea 50-70**: `displayResults()` - Renderiza resultados
- **Línea 88-144**: `verificarCedula()` - Validación dinámica
- **Línea 146-179**: `cargarSolicitudesRecientes()` - Carga cada 30s
- **Línea 182-187**: Auto-carga de solicitudes al iniciar

### styles.css
- **Línea 207-276**: Estilos glassmorphism para tarjeta del asistente
- **Línea 226-255**: Estilos de tarjetas de solicitud con hover
- **Línea 283-298**: Botón de Drive con gradiente
- **Línea 313-329**: Scrollbar personalizado

## 🐛 Problemas Conocidos y Soluciones

### ❌ 403 Error: Service account no tiene permisos
**Causa**: Service account no puede escribir en "Mi unidad" ni en hojas sin permisos
**Solución**:
- Usar Shared Drives únicamente
- Compartir con: `certificados-laborales@certificados-laborales-469714.iam.gserviceaccount.com`
- Delegar escritura de Sheets a Google Apps Script

### ❌ 404 Error: Carpeta no encontrada
**Causa**: DRIVE_FOLDER_ID no existe o no tiene permisos
**Solución**: Verificar que el ID es de Shared Drive y está compartido

### ❌ Caché desactualizada
**Causa**: TTL de 15 minutos puede mostrar datos viejos
**Solución**: Forzar refresh con `_get_cached_contracts(force_refresh=True)`

### ❌ Empresa no normalizada
**Causa**: Alias faltante en hoja "Empresas"
**Solución**: Agregar variante en columna "Empresa" separada por coma

## 🚢 Deployment en Railway

1. Conectar repositorio de GitHub
2. Agregar variables de entorno en Railway Dashboard
3. Railway detecta `requirements.txt` y `Procfile` automáticamente
4. URL: `https://certificadoslaboraleschvs-main-production.up.railway.app/`

## 📝 Notas para Futuros Desarrollos

- La app es **stateless**: no guarda datos localmente, todo en Google Workspace
- El caché global mejora performance pero puede mostrar datos de hace max 15 min
- Los PDFs se generan con ReportLab Platypus (sistema de flowables)
- El frontend usa JavaScript vanilla (sin frameworks)
- Todos los estilos son CSS puro (sin preprocessadores)
- La búsqueda es case-insensitive y sin tildes
- El sistema soporta múltiples contratos por empleado
- Solo se genera carta de recomendación para contratos finalizados

---

**Última actualización**: 2026-02-08
**Versión**: 2.0 (con sistema automatizado y glassmorphism)
