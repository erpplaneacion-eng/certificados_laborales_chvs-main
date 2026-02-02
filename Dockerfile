
# ---- Fase 1: Construir el Entorno Base con Idioma Español ----

# Usamos una imagen oficial de Python, ligera y optimizada
FROM python:3.11-slim

# Establecemos el directorio de trabajo principal dentro del contenedor
WORKDIR /app

# Instalamos los paquetes de idioma español ANTES de hacer cualquier otra cosa
# Esto se ejecuta como administrador (root), por lo que sí tenemos permisos
RUN apt-get update && apt-get install -y locales && \
    sed -i -e 's/# es_ES.UTF-8 UTF-8/es_ES.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

# Configuramos las variables de entorno para que todo el sistema use español
# Esto garantiza que locale.setlocale() en Python funcione correctamente
ENV LANG es_ES.UTF-8
ENV LANGUAGE es_ES:es
ENV LC_ALL es_ES.UTF-8


# ---- Fase 2: Preparar la Aplicación ----

# Copiamos primero el archivo de requerimientos para optimizar el cache de Docker
COPY requirements.txt .

# Instalamos las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos la carpeta principal de la aplicación
COPY ./app /app/app

# ¡LÍNEA CORREGIDA! Copiamos la carpeta con la imagen de la firma
# Sin esta línea, la imagen de la firma no existe dentro del contenedor
COPY ./firma /app/firma


# ---- Fase 3: Ejecutar la Aplicación ----

# Exponemos el puerto que Render usará para comunicarse con nuestra aplicación
# Render asignará dinámicamente el valor a la variable de entorno $PORT
EXPOSE 10000

# El comando final para iniciar el servidor Uvicorn cuando el contenedor se ponga en marcha
# Se adapta dinámicamente al puerto que asigne Railway/Render ($PORT) o usa 10000 por defecto
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]

