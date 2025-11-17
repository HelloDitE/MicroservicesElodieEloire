'''Ce fichier implémente un microservice d’authentification en Flask qui :
- gère l’inscription (/auth/register),
- gère la connexion et renvoie un JWT (/auth/login),
- valide un JWT (/auth/validate),
- stocke les utilisateurs dans une base SQLite (users.db) avec des hashs de mots de passe (bcrypt).'''

# auth_service.py
#Ce code implémente un service d'authentification utilisant Flask, JWT et SQLite.
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
import jwt
import sqlite3
from flask_bcrypt import Bcrypt

# --- 1. Initialisation de l'API ---
auth_app = Flask(__name__)
auth_app.config['SECRET_KEY'] = 'SuperSecretKeyPourTP' # Clé secrète pour signer les JWT
bcrypt = Bcrypt(auth_app) 

# --- 2. Logique de Base de Données (Transfert de database.py) ---
DATABASE_NAME = 'users.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crée la table des utilisateurs si elle n'existe pas."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, password_hash FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user 

def add_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def check_password(hashed_password, password):
    return bcrypt.check_password_hash(hashed_password.encode('utf-8'), password)

# 👈 APPEL CRUCIAL : Assure que la DB est prête avant de traiter les requêtes
init_db() 


# --- 3. Routes de l'Auth Service ---

@auth_app.route('/auth/register', methods=['POST'])
def register():
    """API pour l'inscription."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if get_user_by_username(username):
        return jsonify({"message": "Ce nom d'utilisateur existe déjà."}), 409
        
    if add_user(username, password):
        return jsonify({"message": "Inscription réussie."}), 201
    else:
        return jsonify({"message": "Erreur lors de la création du compte."}), 500

@auth_app.route('/auth/login', methods=['POST'])
def login():
    """API pour la connexion : vérifie et génère un JWT."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
        
    user_record = get_user_by_username(username)
    
    if user_record and check_password(user_record['password_hash'], password):
        # Génération du JWT (Valable 1 heure)
        payload = {
            'user': username,
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
            'iat': datetime.now(timezone.utc)
        }
        
        token = jwt.encode(payload, auth_app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({
            'message': 'Connexion réussie',
            'token': token
        }), 200
    else:
        return jsonify({'message': "Nom d'utilisateur ou mot de passe incorrect."}, 401)

@auth_app.route('/auth/validate', methods=['POST'])
def validate_token():
    """API pour valider un JWT (sera utilisée par l'API Gateway)."""
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({"message": "Token manquant."}), 400
    
    try:
        payload = jwt.decode(token, auth_app.config['SECRET_KEY'], algorithms=['HS256'])
        return jsonify({
            "message": "Token valide",
            "user": payload['user'] 
        }), 200
    
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expiré."}), 401
    except Exception:
        return jsonify({"message": "Token invalide."}), 401

if __name__ == '__main__':
    # Le Auth Service s'exécute sur le port 5002
    auth_app.run(debug=True, port=5002)