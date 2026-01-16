from fastapi import FastAPI, Request
import uvicorn
import requests
import json
import logging

# Configuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NavrosBackend")

# URL interna de Docker para hablar con el bot
# Como están en la misma red 'coolify', usamos el nombre del contenedor
WHATSAPP_API_URL = "http://whatsapp-manual:3000/message/navros/text"

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Backend Navros con IA (Básico) Operativo"}

def enviar_respuesta(remote_jid, texto):
    """Envía un mensaje de vuelta usando el contenedor de WhatsApp"""
    try:
        payload = {"to": remote_jid, "text": texto}
        # Enviamos la petición al contenedor vecino
        r = requests.post(WHATSAPP_API_URL, json=payload)
        logger.info(f"Respuesta enviada a {remote_jid}: {r.status_code}")
    except Exception as e:
        logger.error(f"Error enviando respuesta: {e}")

@app.post("/webhook/whatsapp")
async def receive_whatsapp(request: Request):
    try:
        body = await request.json()
        data = body.get("data", {})
        key = data.get("key", {})
        
        # 1. FILTROS DE SEGURIDAD
        # Ignorar mensajes enviados por mí mismo (para evitar bucles infinitos)
        if key.get("fromMe") is True:
            return {"status": "ignored_self"}
            
        # Ignorar actualizaciones de estado o historial (sin contenido)
        if not data.get("message"):
            return {"status": "ignored_system"}

        # 2. EXTRAER DATOS
        sender = key.get("remoteJid") # El ID del usuario (ej: 57300...@s.whatsapp.net)
        message_content = data.get("message", {})
        
        # Intentar leer texto (puede venir como 'conversation' o 'extendedTextMessage')
        texto_usuario = message_content.get("conversation")
        if not texto_usuario:
            texto_usuario = message_content.get("extendedTextMessage", {}).get("text")
            
        if not texto_usuario:
            return {"status": "ignored_no_text"}

        print(f"📩 Mensaje de {sender}: {texto_usuario}")

        # 3. CEREBRO (Lógica simple por ahora)
        texto_lower = texto_usuario.lower().strip()
        respuesta = ""

        if "hola" in texto_lower:
            respuesta = "¡Hola! Soy Navros v1.0, tu asistente en Docker. 🤖✨"
        elif "ping" in texto_lower:
            respuesta = "¡Pong! 🏓 Estoy escuchando fuerte y claro."
        elif "navros" in texto_lower:
            respuesta = "¡Presente! ¿En qué puedo ayudarte hoy?"
        else:
            # Opcional: Respuesta por defecto o silencio
            # respuesta = "No entendí eso, pero estoy aprendiendo."
            pass

        # 4. RESPONDER (Si hay algo que decir)
        if respuesta:
            enviar_respuesta(sender, respuesta)

        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error procesando: {e}")
        return {"status": "error"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
