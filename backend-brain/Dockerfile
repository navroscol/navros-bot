FROM python:3.9-slim

WORKDIR /app

# Instalar librerías
RUN pip install fastapi uvicorn requests

# Copiar el código
COPY main.py .

# Exponer el puerto 8000 (El que espera WhatsApp)
EXPOSE 8000

CMD ["python", "main.py"]
