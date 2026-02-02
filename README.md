# Aplicación Avanzada para Generar Certificados Laborales

Esta es una aplicación web sofisticada construida con FastAPI que genera certificados laborales profesionales en formato PDF. La aplicación incluye una interfaz interactiva, lógica de negocio avanzada, normalización inteligente de datos y generación condicional de contenido.

## Características Principales

- 🌐 **Interfaz Interactiva**: Verificación automática de datos al introducir cédula
- 🏢 **Normalización de Empresas**: Agrupación inteligente por entidades legales reales
- 📄 **Múltiples Certificados**: Un PDF consolidado por cada empresa donde trabajó el empleado
- 💰 **Entrada Condicional**: Campo de salario manual para casos específicos
- 🎨 **Maquetación Profesional**: PDFs con texto justificado y márgenes respetados
- 📅 **Fechas Localizadas**: Formato de fechas en español con nombres de meses completos
- 💬 **Conversión a Letras**: Salarios expresados en números y palabras

## Arquitectura

La aplicación implementa una arquitectura de 3 capas con separación clara de responsabilidades:

### 1. Capa de Presentación (Frontend)
- **Formulario Interactivo**: `app/templates/form.html` con JavaScript para verificación en tiempo real
- **UI Responsiva**: Diseño moderno con CSS personalizado
- **UX Intuitiva**: Campos condicionales y validación automática

### 2. Capa de Lógica de Negocio (Backend)
- **Framework**: FastAPI con endpoints RESTful
- **Servicios Especializados**:
  - `sheets_service.py`: Conexión a Google Sheets con normalización de datos
  - `template.py`: Generación de PDFs usando ReportLab Platypus
  - `drive_service.py`: Upload a Google Drive
- **Lógica de Negocio Avanzada**:
  - Agrupación por nombres canónicos de empresa
  - Renderizado condicional basado en tipo de cargo y estado del contrato
  - Formateo inteligente de fechas y números

### 3. Capa de Datos (Almacenamiento)
- **Google Sheets**: Dos hojas de cálculo interconectadas
  - `bd_contratacion`: Historial de contratos por empleado
  - `Empresas`: Tabla de mapeo empresa-NIT con soporte para alias
- **Google Drive**: Almacenamiento de PDFs con nombres descriptivos

## Estructura de Archivos

```
.env                        # Variables de entorno (NO subir a git)
requirements.txt            # Dependencias de Python incluyendo num2words
app/
├── main.py                 # Endpoints FastAPI y lógica de negocio avanzada
├── config.py               # Configuración con pydantic-settings
├── google_clients.py       # Autenticación y clientes de Google APIs
├── services/               # Lógica de negocio modularizada
│   ├── sheets_service.py   # Acceso a Google Sheets con normalización
│   ├── template.py         # Generación de PDFs con ReportLab Platypus
│   └── drive_service.py    # Upload a Google Drive
└── templates/
    └── form.html           # Interfaz interactiva con JavaScript
```

## Cómo Configurar y Ejecutar

### 1. Crear un Entorno Virtual
```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
```

### 2. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno
Crea un archivo llamado `.env` en la raíz del proyecto con las siguientes variables:

```env
GOOGLE_CREDENTIALS_JSON='{"type": "service_account", ...}'  # Credenciales de Google en una línea
SHEET_ID="tu_id_de_google_sheets"
DRIVE_FOLDER_ID="tu_id_de_carpeta_google_drive"
```

### 4. Configurar Google Sheets
Asegúrate de que tu Google Sheet tenga dos hojas:

#### Hoja `bd_contratacion`:
| cedula | Nombre del empleado | Desc. Cargo | SALARIO BASICO | Fecha de Ingreso | Fecha de Retiro | Nombre de empresa |
|--------|-------------------|-------------|----------------|------------------|-----------------|-------------------|
| 12345678 | Juan Pérez | MANIPULADORA ALIMENTOS | $2400000 | 20240101 | | CORPORACION |

#### Hoja `Empresas`:
| Empresa | Nit |
|---------|-----|
| CORPORACION HACIA UN VALLE SOLIDARIO,CORPORACION | 805.029.170-0 |

### 5. Ejecutar la Aplicación
```bash
uvicorn app.main:app --reload
```

### 6. Usar la Aplicación
1. Abre tu navegador y ve a `http://127.0.0.1:8000`
2. Introduce una cédula
3. La aplicación verificará automáticamente la información
4. Si es necesario, completa el campo de salario (solo para MANIPULADORA ALIMENTOS activos)
5. Genera los certificados consolidados

## Lógica de Negocio

### Normalización de Empresas
- Los alias de empresa se resuelven a nombres canónicos usando la hoja `Empresas`
- Contratos con diferentes nombres de empresa pero mismo NIT se consolidan en un único certificado

### Renderizado Condicional
- **Salario**: Solo aparece si el contrato está activo (Fecha de Retiro vacía)
- **Texto dinámico**: Cambia según el tipo de cargo (PAE vs empresa específica)
- **Períodos detallados**: Incluyen cargo específico en cada período laboral

### Formateo Inteligente
- **Fechas**: De YYYYMMDD a "01 de febrero de 2024"
- **Números**: Días en formato de palabras ("veintidós")
- **Salarios**: En formato numérico y convertidos a letras en español

## Dependencias Clave

- **FastAPI**: Framework web moderno
- **ReportLab**: Generación avanzada de PDFs
- **num2words**: Conversión de números a palabras en español
- **gspread**: Integración con Google Sheets
- **pydantic-settings**: Gestión de configuración

## Flujo de Trabajo

1. **Verificación**: Usuario introduce cédula → API verifica en Google Sheets
2. **Normalización**: Nombres de empresa se resuelven a entidades canónicas
3. **Agrupación**: Contratos se agrupan por empresa normalizada
4. **Generación**: Un PDF consolidado por empresa con lógica condicional
5. **Upload**: PDFs se suben a Google Drive con enlaces directos
6. **Respuesta**: Lista de todos los certificados generados

Esta aplicación representa una solución empresarial completa para la generación automatizada de certificados laborales con alta calidad visual y lógica de negocio sofisticada.