import firebase_admin
from firebase_admin import credentials

# Initialisation de Firebase Admin
cred = credentials.Certificate('credentials.json')
firebase_admin.initialize_app(cred)

# Configuration MQTT
MQTT_BROKER = "broker.mqtt.com"
MQTT_PORT = 1883
MQTT_TOPIC = "topic/test"
