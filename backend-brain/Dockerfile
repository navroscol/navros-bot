FROM python:3.9-slim

WORKDIR /app

# Agregamos 'openai' a las instalaciones
RUN pip install fastapi uvicorn requests openai

COPY main.py .

EXPOSE 8000

CMD ["python", "main.py"]
