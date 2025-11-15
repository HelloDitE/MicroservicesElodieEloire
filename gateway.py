# gateway.py
from flask import Flask, request, jsonify, abort
import requests

# --- Initialisation de l'API Gateway ---
gateway_app = Flask(__name__)

# --- Configuration des Microservices (URLs internes) ---
AUTH_SERVICE_URL = 'http://localhost:5002/auth' 
ORDERS_SERVICE_URL = 'http://localhost:5001' # Base URL pour l'Orders Service


# --- Middleware de validation de Token ---
# Cette fonction sera appelée avant de router la requête à l'Orders Service
def validate_and_get_user():
    # 1. Tenter de récupérer le JWT du header 'Authorization'
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        # Si le header est absent ou mal formé, la validation échoue
        return None, "Token JWT manquant ou format invalide (Bearer requis)."

    token = auth_header.split(' ')[1]
    
    # 2. Appeler l'Auth Service pour valider le token
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/validate",
            json={'token': token}
        )
        
        if response.status_code == 200:
            # Token valide, retourne le nom d'utilisateur extrait
            return response.json().get('user'), None
        else:
            # Token invalide (expiré, signature incorrecte)
            return None, response.json().get('message', "Token invalide.")
            
    except requests.exceptions.ConnectionError:
        return None, "Erreur de connexion : Auth Service indisponible."


# --- ROUTE PRINCIPALE DU GATEWAY ---
# Le gateway intercepte toutes les requêtes destinées aux commandes.
# Ex: Si le client appelle POST /api/orders, le gateway intercepte.

@gateway_app.route('/api/orders', methods=['POST'])
def handle_submit_order():
    # 1. Validation de l'authentification (Sécurité)
    user, error = validate_and_get_user()
    
    if error:
        # 401 Unauthorized si le token est invalide ou absent
        return jsonify({"message": f"Accès refusé. {error}"}), 401
    
    # 2. Ajout de l'utilisateur validé aux données de la requête (Enrichissement)
    # On force l'utilisateur dans le payload pour s'assurer qu'il correspond au token
    payload = request.get_json()
    payload['user'] = user
    
    # 3. Routage vers le Orders Service (API métier)
    try:
        # Envoie la requête au Orders Service (port 5001)
        response = requests.post(f"{ORDERS_SERVICE_URL}/orders", json=payload)
        
        # 4. Retourne la réponse du service au client
        # Utilise .content et .status_code pour transmettre la réponse binaire/JSON et le statut exact
        return response.content, response.status_code, response.headers.items()
        
    except requests.exceptions.ConnectionError:
        return jsonify({"message": "Orders Service indisponible."}, 503)


# Vous pouvez ajouter d'autres routes ici (ex: GET /api/orders/<user> pour l'historique)
# ...

if __name__ == '__main__':
    # Le Gateway s'exécute sur le port 5003
    print("API Gateway démarrée sur http://localhost:5003")
    gateway_app.run(debug=True, port=5003)