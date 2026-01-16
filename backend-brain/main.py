from fastapi import FastAPI, Request
import uvicorn
import requests
import json
import logging
import os
from openai import OpenAI

# Configuración de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NavrosAI")

# CONEXIÓN CON WHATSAPP
WHATSAPP_API_URL = "http://whatsapp-manual:3000/message/navros/text"

# CONEXIÓN CON OPENAI (Lee la clave desde el sistema, no del código)
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

app = FastAPI()

def enviar_respuesta(remote_jid, texto):
    try:
        requests.post(WHATSAPP_API_URL, json={"to": remote_jid, "text": texto})
    except Exception as e:
        logger.error(f"Error enviando respuesta: {e}")

def consultar_chatgpt(mensaje_usuario):
    if not api_key:
        return "⚠️ Error: No configuraste la API Key de OpenAI en el servidor."
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Puedes cambiar a "gpt-4o" si tienes créditos
            messages=[
                {
                    "role": "system", 
                    "content": "Eres Navros, un asistente útil, sarcástico y breve que vive en un servidor Docker. Responde siempre en español y usa emojis."
                },
                {"role": "user", "content": mensaje_usuario}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Me dio un calambre cerebral (Error OpenAI): {str(e)}"

@app.post("/webhook/whatsapp")
async def receive_whatsapp(request: Request):
    try:
        body = await request.json()
        data = body.get("data", {})
        key = data.get("key", {})
        
        # Ignorar mis propios mensajes y mensajes de sistema
        if key.get("fromMe") or not data.get("message"):
            return {"status": "ignored"}

        sender = key.get("remoteJid")
        
        # Extraer texto
        msg_obj = data.get("message", {})
        texto = msg_obj.get("conversation") or msg_obj.get("extendedTextMessage", {}).get("text")
        
        if not texto:
            return {"status": "no_text"}

        print(f"📩 Consulta de {sender}: {texto}")

        # --- CEREBRO IA ---
        respuesta_ia = consultar_chatgpt(texto)
        enviar_respuesta(sender, respuesta_ia)

        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error crítico: {e}")
        return {"status": "error"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
