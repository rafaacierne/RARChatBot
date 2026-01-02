import os
from flask import Flask, request, jsonify
import google.generativeai as genai
import requests

app = Flask(__name__)

# --- VARIABLES DE ENTORNO ---
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- CONFIGURACIÓN GEMINI IA ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

SYSTEM_PROMPT = """
ROL: Asistente virtual de RAR INFORMÁTICA (Chivilcoy).
UBICACIÓN: Av. Echeverría 192, al lado del Super 6.
HORARIOS: L-V 9-12 y 16-20, Sáb 9-12:30.
SERVICIOS: Reparación PC/Notebooks, Insumos, Redes Corporativas (Mikrotik/VLANs).
POLÍTICA: Diagnóstico SIN CARGO. No dar precios de reparación sin ver el equipo.
SI NO SABES: Decir "Dejame que le consulto a Rafael".
TONO: Profesional, breve y amable.
"""

def consultar_gemini(mensaje_cliente):
    try:
        chat = model.start_chat(history=[])
        prompt = f"{SYSTEM_PROMPT}\n\nCliente dice: {mensaje_cliente}\nRespuesta:"
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        print(f"Error Gemini: {e}")
        return "Disculpa, tuve un error técnico. ¿Me podrías repetir la pregunta?"

def enviar_whatsapp(telefono, texto):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto}
    }
    response = requests.post(url, headers=headers, json=data)
    return response

# --- WEBHOOK (VERIFICACIÓN) ---
@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Error de verificación", 403

# --- WEBHOOK (MENSAJES) ---
@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    body = request.get_json()
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" in value:
            mensaje = value["messages"][0]
            telefono = mensaje["from"]
            texto = mensaje["text"]["body"]
            
            # 1. Consultar IA
            respuesta = consultar_gemini(texto)
            # 2. Responder en WhatsApp
            enviar_whatsapp(telefono, respuesta)
            
    except Exception as e:
        pass 

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
