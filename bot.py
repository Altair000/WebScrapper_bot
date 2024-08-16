import telebot
import requests
import os
from bs4 import BeautifulSoup
from flask import Flask, request

# Reemplaza 'YOUR_TELEGRAM_BOT_TOKEN' con el token de tu bot de Telegram
app = Flask(__name__)
TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot("TOKEN")
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "¡Mensaje recibido!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://webscrapperbot-7376c5dc3c12.herokuapp.com/' + TOKEN)
    return "¡Webhook configurado!", 200

# Diccionario para almacenar datos temporales del usuario
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "¡Hola! Envíame una URL para analizar.")

@bot.message_handler(func=lambda message: True)
def analyze_url(message):
    chat_id = message.chat.id
    text = message.text
    
    if chat_id in user_data and 'step' in user_data[chat_id]:
        if user_data[chat_id]['step'] == 'analyze':
            handle_tag_selection(message)
        elif user_data[chat_id]['step'] == 'endpoints':
            handle_endpoint_selection(message)
    else:
        try:
            response = requests.get(text)
            soup = BeautifulSoup(response.content, 'html.parser')
            user_data[chat_id] = {'soup': soup, 'url': text, 'step': 'analyze'}
            bot.reply_to(message, "Página analizada. Por favor, introduce el tipo de datos que deseas obtener (e.g., 'h1', 'p', 'a').")
        except Exception as e:
            bot.reply_to(message, f"Error al analizar la URL: {e}")

def handle_tag_selection(message):
    chat_id = message.chat.id
    soup = user_data[chat_id]['soup']
    tag = message.text
    elements = soup.find_all(tag)
    
    if elements:
        response = ""
        for i, elem in enumerate(elements):
            response += f"Elemento {i+1}: {elem.text.strip()}\n"
        bot.reply_to(message, response)
        
        bot.reply_to(message, "¿Quieres obtener los endpoints de la página? Envíame 'sí' o 'no'.")
        user_data[chat_id]['step'] = 'endpoints'
    else:
        bot.reply_to(message, f"No se encontraron elementos con la etiqueta '{tag}'.")

def handle_endpoint_selection(message):
    chat_id = message.chat.id
    if message.text.lower() == 'sí':
        soup = user_data[chat_id]['soup']
        endpoints = [a['href'] for a in soup.find_all('a', href=True)]
        if endpoints:
            response = "Endpoints encontrados:\n"
            for endpoint in endpoints:
                response += f"{endpoint}\n"
            bot.reply_to(message, response)
            
            bot.reply_to(message, "Selecciona un endpoint de la lista para analizar.")
            user_data[chat_id]['step'] = 'select_endpoint'
            user_data[chat_id]['endpoints'] = endpoints
        else:
            bot.reply_to(message, "No se encontraron endpoints en la página.")
    elif user_data[chat_id]['step'] == 'select_endpoint':
        endpoint = message.text
        if endpoint in user_data[chat_id]['endpoints']:
            url = user_data[chat_id]['url'] + endpoint
            try:
                response = requests.get(url)
                headers = response.headers
                payload = response.request.body or "No payload"
                bot.reply_to(message, f"Headers: {headers}")
                bot.reply_to(message, f"Payload: {payload}")
                bot.reply_to(message, f"Response: {response.text}")
            except Exception as e:
                bot.reply_to(message, f"Error al acceder al endpoint: {e}")
        else:
            bot.reply_to(message, "El endpoint seleccionado no es válido.")
    else:
        bot.reply_to(message, "Operación cancelada. Envíame una nueva URL para comenzar.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 5000)))
