from flask import Flask, request, jsonify
import os
from openai import OpenAI
import requests
import base64
import tempfile
import json
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
XAI_API_KEY = os.environ.get('XAI_API_KEY') 

openai_client = OpenAI(api_key=OPENAI_API_KEY)
grok_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1") if XAI_API_KEY else None

WHATSAPP_ENGINE_URL = "http://whatsapp-manual:3000"

conversation_history = {}
user_audio_preference = {}

def send_whatsapp_message(phone_number, message):
    try:
        requests.post(f"{WHATSAPP_ENGINE_URL}/message/text", json={"to": phone_number, "text": message})
    except Exception as e:
        print(f"❌ Error texto: {e}")

def send_whatsapp_media(phone_number, media_type, file_data, caption=""):
    try:
        url = f"{WHATSAPP_ENGINE_URL}/message/media"
        data = {
            "to": phone_number,
            "type": media_type,
            "base64": file_data,
            "caption": caption
        }
        requests.post(url, json=data)
        print(f"✅ Multimedia ({media_type}) enviada.")
    except Exception as e:
        print(f"❌ Error multimedia: {e}")

def generate_image(prompt):
    try:
        print(f"🎨 Generando imagen: {prompt}")
        response = openai_client.images.generate(
            model="dall-e-3", prompt=prompt, size="1024x1024", quality="standard", n=1, response_format="b64_json"
        )
        return response.data[0].b64_json
    except Exception as e:
        print(f"❌ Error DALL-E: {e}")
        return None

def transcribe_audio(media_data):
    try:
        if not media_data or not media_data.get('base64'): return None
        audio_bytes = base64.b64decode(media_data.get('base64'))
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_path = temp_audio.name
        
        with open(temp_path, 'rb') as f:
            transcript = openai_client.audio.transcriptions.create(model="whisper-1", file=f)
        os.unlink(temp_path)
        return transcript.text
    except Exception as e:
        print(f"❌ Error Whisper: {e}")
        return None

def text_to_speech(text):
    try:
        # CAMBIO CLAVE: Pedimos 'opus' en lugar de mp3 por defecto
        response = openai_client.audio.speech.create(
            model="tts-1", 
            voice="nova", 
            input=text,
            response_format="mp3" 
        )
        return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        print(f"❌ Error TTS: {e}")
        return None

def get_chatgpt_response(message, phone_number, will_be_audio=False):
    if phone_number not in conversation_history: conversation_history[phone_number] = []
    
    sys_prompt = "Eres NAVROS, asistente de la marca de streetwear Navros. Estilo urbano. Responde útilmente."
    if will_be_audio: sys_prompt += " RESPUESTA PARA AUDIO: Sé muy breve (máx 30 palabras)."

    messages = [{"role": "system", "content": sys_prompt}] + conversation_history[phone_number][-6:]
    messages.append({"role": "user", "content": message})

    client_use = grok_client if grok_client else openai_client
    model_use = "grok-4-fast-reasoning" if grok_client else "gpt-3.5-turbo"

    try:
        resp = client_use.chat.completions.create(model=model_use, messages=messages, max_tokens=300)
        reply = resp.choices[0].message.content
        conversation_history[phone_number].append({"role": "user", "content": message})
        conversation_history[phone_number].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return "Error procesando tu mensaje."

@app.route('/webhook/whatsapp', methods=['POST'])
def webhook():
    try:
        data = request.json
        msg_data = data.get("data", {})
        media_data = data.get("media")
        key = msg_data.get("key", {})
        
        if key.get("fromMe"): return jsonify({"status": "ignored"}), 200
        sender = key.get("remoteJid")
        
        msg_obj = msg_data.get("message", {})
        text = msg_obj.get("conversation") or msg_obj.get("extendedTextMessage", {}).get("text")
        
        is_audio_msg = 'audioMessage' in msg_obj
        if is_audio_msg and media_data:
            text = transcribe_audio(media_data)

        if not text: return jsonify({"status": "no_text"}), 200
        print(f"📩 {sender}: {text}")

        text_lower = text.lower()
        if any(x in text_lower for x in ["genera una imagen", "crea una imagen", "dibújame", "dibujame"]):
            send_whatsapp_message(sender, "🎨 Dame un momento...")
            image_b64 = generate_image(text)
            if image_b64:
                send_whatsapp_media(sender, "image", image_b64, caption="By Navros AI")
            else:
                send_whatsapp_message(sender, "Error generando imagen.")
            return jsonify({"status": "ok"}), 200

        wants_audio = user_audio_preference.get(sender, False) or is_audio_msg or "audio" in text_lower
        reply = get_chatgpt_response(text, sender, will_be_audio=wants_audio)

        if wants_audio:
            audio_b64 = text_to_speech(reply)
            if audio_b64:
                send_whatsapp_media(sender, "audio", audio_b64)
            else:
                send_whatsapp_message(sender, reply)
        else:
            send_whatsapp_message(sender, reply)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"Error webhook: {e}")
        return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
