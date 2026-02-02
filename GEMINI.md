# Certificados Laborales CHVS

## Project Overview
This project is an advanced web application designed to generate professional labor certificates in PDF format. It automates the process by retrieving employee data from Google Sheets, normalizing company information, and generating consolidated certificates. The generated PDFs are then uploaded to Google Drive.

The application uses **FastAPI** for the backend, **ReportLab** for PDF generation, and integrates seamlessly with **Google Sheets** and **Google Drive**.

## Key Features
*   **Interactive Interface:** Web form for user input (ID verification).
*   **Data Normalization:** Intelligent grouping of company names to legal entities.
*   **PDF Generation:** Professional layout with justified text, conditional content (e.g., salary visibility), and localized formatting (Spanish).
*   **Cloud Integration:**
    *   Reads employee contracts and company data from **Google Sheets**.
    *   Uploads generated certificates to **Google Drive**.
*   **Localization:** Full Spanish support for dates and number-to-word conversions.

## Tech Stack
*   **Backend Framework:** FastAPI (`app/main.py`)
*   **PDF Engine:** ReportLab (`app/services/template.py`)
*   **Google Integration:** `gspread` (Sheets), `google-api-python-client` (Drive)
*   **Server:** Uvicorn
*   **Containerization:** Docker

## Project Structure

```
├── app/
│   ├── config.py             # Configuration management (Pydantic settings)
│   ├── google_clients.py     # Google API authentication & clients
│   ├── main.py               # FastAPI entry point & API endpoints
│   ├── services/             # Core business logic
│   │   ├── drive_service.py  # Google Drive upload logic
│   │   ├── sheets_service.py # Google Sheets data retrieval & normalization
│   │   └── template.py       # PDF generation (ReportLab)
│   └── templates/
│       └── form.html         # Frontend HTML template
├── firma/                    # Directory containing signature assets
├── build.sh                  # Build script (installs deps & locales)
├── Dockerfile                # Docker configuration for deployment
├── requirements.txt          # Python dependencies
└── .env                      # Environment variables (not committed)
```

## Setup & Installation

### Local Development

1.  **Create a Virtual Environment:**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration (.env):**
    Create a `.env` file in the root directory with the following variables:
    ```env
    GOOGLE_CREDENTIALS_JSON='{"type": "service_account", ...}'
    SHEET_ID="your_google_sheet_id"
    DRIVE_FOLDER_ID="your_google_drive_folder_id"
    ```

4.  **Run the Application:**
    ```bash
    uvicorn app.main:app --reload
    ```
    Access the app at `http://127.0.0.1:8000`.

### Docker Deployment

The project includes a `Dockerfile` optimized for production (using `python:3.11-slim`) with correct locale configuration for Spanish.

1.  **Build the Image:**
    ```bash
    docker build -t certificados-chvs .
    ```

2.  **Run the Container:**
    ```bash
    docker run -p 10000:10000 --env-file .env certificados-chvs
    ```

## Key Workflows

1.  **User Input:** User enters an ID in the web form (`/`).
2.  **Verification:** The app checks the ID against the `bd_contratacion` sheet in Google Sheets.
3.  **Processing:**
    *   Data is normalized using the `Empresas` sheet to resolve aliases.
    *   Contracts are grouped by the legal entity.
4.  **Generation:** PDF certificates are generated using ReportLab, converting numbers to words and formatting dates in Spanish.
5.  **Delivery:** PDFs are uploaded to the specified Google Drive folder, and download links are provided to the user.

## Development Notes
*   **Locales:** The application strictly requires `es_ES.UTF-8` locale for correct date and number formatting. This is handled automatically in the `Dockerfile` and `build.sh`.
*   **Signature:** Ensure the `firma/` directory contains the necessary signature images (`firma.jpg` or `firma.png`) as referenced in the code.
