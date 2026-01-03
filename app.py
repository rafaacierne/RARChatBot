import os
from flask import Flask, request, jsonify
import requests # Usamos requests para todo, chau librería de Google

app = Flask(__name__)

# --- VARIABLES DE ENTORNO ---
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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
        # --- PETICIÓN DIRECTA HTTP (REST API) ---
        # Esto evita cualquier error de la librería de Python.
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        prompt_completo = f"{SYSTEM_PROMPT}\n\nCliente dice: {mensaje_cliente}\nRespuesta:"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt_completo}]
            }]
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # Navegamos el JSON de respuesta de Google
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except:
                return "Recibí respuesta vacía de la IA."
        else:
            print(f"Error HTTP Gemini: {response.status_code} - {response.text}")
            return "Error de conexión con la IA."
            
    except Exception as e:
        print(f"Error General: {e}")
        return "Disculpa, estoy reiniciando mis sistemas."

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
    try:
        response = requests.post(url, headers=headers, json=data)
        return response
    except Exception as e:
        print(f"Error enviando WhatsApp: {e}")
        return None

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
        if "entry" in body:
            entry = body["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]
            
            if "messages" in value:
                mensaje = value["messages"][0]
                telefono = mensaje["from"]
                
                if mensaje["type"] == "text":
                    texto = mensaje["text"]["body"]
                    # 1. Consultar IA (Método directo)
                    respuesta = consultar_gemini(texto)
                    # 2. Responder
                    enviar_whatsapp(telefono, respuesta)
                
    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        pass 

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
