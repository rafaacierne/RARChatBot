
import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# --- VARIABLES ---
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
    # ESTRATEGIA FINAL: Usar los ALIAS GENÉRICOS que aparecieron en tu diagnóstico.
    # Estos apuntan automáticamente a la versión estable permitida para tu cuenta.
    modelos = ["gemini-flash-latest", "gemini-pro-latest"]
    
    prompt_completo = f"{SYSTEM_PROMPT}\n\nCliente dice: {mensaje_cliente}\nRespuesta:"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_completo}]
        }]
    }
    headers = {'Content-Type': 'application/json'}

    for modelo in modelos:
        try:
            # URL estándar
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_API_KEY}"
            
            print(f"Probando con: {modelo}...")
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except:
                    print(f"Modelo {modelo} devolvió JSON vacío.")
                    continue
            else:
                # Si falla (429 quota, 404 not found), probamos el siguiente
                print(f"Error en {modelo}: {response.status_code} - {response.text}")
                continue
                
        except Exception as e:
            print(f"Excepción en {modelo}: {e}")
            continue

    return "Disculpa, nuestros sistemas están saturados en este momento. Intenta en un rato."

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
        requests.post(url, headers=headers, json=data)
    except Exception as e:
        print(f"Error WhatsApp: {e}")

# --- WEBHOOK ---
@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Error", 403

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
                tel = mensaje["from"]
                if mensaje["type"] == "text":
                    texto = mensaje["text"]["body"]
                    # Consultar IA
                    respuesta = consultar_gemini(texto)
                    # Responder
                    enviar_whatsapp(tel, respuesta)
    except Exception as e:
        print(f"Error procesando: {e}")
        pass
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
