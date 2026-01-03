import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# --- VARIABLES ---
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- FUNCIÓN DE DIAGNÓSTICO ---
def listar_modelos_disponibles():
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        response = requests.get(url)
        
        print("--- DIAGNÓSTICO DE API KEY ---")
        if response.status_code == 200:
            data = response.json()
            if "models" in data:
                print("Modelos habilitados para tu clave:")
                for m in data["models"]:
                    print(f" - {m['name']}")
                return "Clave funcionando. Revisa los logs."
            else:
                print("La clave funciona pero NO DEVUELVE modelos. ¿Proyecto vacío?")
                return "Clave sin modelos."
        else:
            print(f"ERROR GRAVE DE CLAVE: {response.status_code}")
            print(f"Mensaje: {response.text}")
            return f"Error de Clave: {response.status_code}"
            
    except Exception as e:
        print(f"Error conectando: {e}")
        return "Error de conexión."

def consultar_gemini(mensaje):
    # Intentamos con el modelo más básico si el diagnóstico falla
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": mensaje}]}]}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        pass
    return "Estoy en modo diagnóstico. Revisa los logs de Render para ver qué modelos tienes."

def enviar_whatsapp(telefono, texto):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": telefono, "type": "text", "text": {"body": texto}}
    requests.post(url, headers=headers, json=data)

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    if mode == "subscribe" and token == VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    return "Error", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    # AL RECIBIR MENSAJE, EJECUTAMOS EL DIAGNÓSTICO
    listar_modelos_disponibles()
    
    # Respondemos algo genérico para no dejar colgado a WhatsApp
    body = request.get_json()
    try:
        entry = body["entry"][0]["changes"][0]["value"]
        if "messages" in entry:
            tel = entry["messages"][0]["from"]
            enviar_whatsapp(tel, "Diagnóstico ejecutado. Mira la consola de Render.")
    except: pass
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
