import requests
import random
import time

# URL de votre route Flask pour recevoir le message
url = "http://127.0.0.1:5000/api/receive_message"

# Fonction pour générer une fréquence cardiaque réaliste (en bpm)
def generate_random_heart_rate():
    # Plage réaliste de fréquence cardiaque entre 60 et 100 bpm au repos
    return random.randint(60, 100)

# Fonction pour générer un SPO2 réaliste
def generate_random_spo2():
    # Plage réaliste de SPO2 entre 90% et 100%
    return random.randint(90, 100)

# Envoi de 6 messages simulant des valeurs aléatoires
for i in range(6):
    # Décider aléatoirement si on envoie un message de fréquence cardiaque ou de SPO2
    if random.choice([True, False]):  # Choisir aléatoirement entre fréquence cardiaque ou SPO2
        # Simuler un message de fréquence cardiaque
        random_heart_rate = generate_random_heart_rate()
        message_data = {
            "message": random_heart_rate,  # La valeur de la fréquence cardiaque
            "topic": "heart_rate"  # Topic pour la fréquence cardiaque
        } 
        print(f"Envoi du message {i+1} - Fréquence cardiaque: {random_heart_rate} bpm")
    else:
        # Simuler un message de SPO2
        random_spo2 = generate_random_spo2()
        message_data = { 
            "message": random_spo2,  # La valeur du SPO2
            "topic": "spo2"  # Topic pour SPO2
        }
        print(f"Envoi du message {i+1} - SPO2: {random_spo2}%")

    # Envoyer une requête POST avec le message
    response = requests.post(url, json=message_data)

    # Afficher la réponse du serveur
    if response.status_code == 200:
        print(f"Message {i+1} envoyé avec succès!")
    else:
        print(f"Erreur lors de l'envoi du message {i+1}: {response.status_code}")
    
    # Attendre un peu avant d'envoyer le message suivant (1 seconde)
    time.sleep(1)
