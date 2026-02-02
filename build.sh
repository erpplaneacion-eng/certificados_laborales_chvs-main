```bash
#!/usr/bin/env bash
# exit on error
set -o errexit

echo "--- Iniciando el script de construcción ---"

# 1. Instala las dependencias de Python
echo "Instalando dependencias de Python..."
pip install -r requirements.txt

# 2. Instala las herramientas de sistema y el idioma español
echo "Actualizando el sistema e instalando locales..."
apt-get update && apt-get install -y locales

# 3. Configura el idioma español para que Python lo pueda usar
echo "Configurando idioma es_ES.UTF-8..."
sed -i -e 's/# es_ES.UTF-8 UTF-8/es_ES.UTF-8 UTF-8/' /etc/locale.gen
dpkg-reconfigure --frontend=noninteractive locales
update-locale LANG=es_ES.UTF-8

echo "--- Script de construcción finalizado con éxito ---"
```3.  **Guarda y cierra el archivo.**

---