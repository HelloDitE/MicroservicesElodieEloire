"""
Ce fichier implémente un microservice d’authentification en Flask qui :
- gère l’inscription (/auth/register),
- gère la connexion et renvoie un JWT (/auth/login),
- valide un JWT (/auth/validate),
- gère un refresh token (/auth/refresh),
- stocke les utilisateurs et tokens dans SQLite.
"""
# auth_service.py
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from authlib.jose import jwt, JoseError
import sqlite3
from flask_bcrypt import Bcrypt
from functools import wraps

# --- 1. Initialisation de l'API ---
auth_app = Flask(__name__)
auth_app.config['SECRET_KEY'] = 'SuperSecretKeyPourTP'
bcrypt = Bcrypt(auth_app)

# --- 2. Base de données SQLite ---
DATABASE_NAME = 'users.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crée les tables si elles n'existent pas."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            token TEXT NOT NULL,
            expires_at TEXT NOT NULL
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

# Initialisation DB
init_db()


# ================================
#  Décorateur d'authentification
# ================================
def require_auth(func):
    """
    Vérifie que le JWT envoyé dans le header Authorization est valide.
    Décorateur réutilisable pour protéger n'importe quelle route.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"message": "Token manquant"}), 401

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"message": "Format du token invalide"}), 401

        token = parts[1]

        try:
            payload = jwt.decode(token, auth_app.config['SECRET_KEY'])
            return func(payload, *args, **kwargs)
        except JoseError:
            return jsonify({"message": "Token invalide ou expiré"}), 401

    return wrapper


# ================================
#  ROUTES PUBLIQUES
# ================================

@auth_app.route('/auth/register', methods=['POST'])
def register():
    """Inscription utilisateur"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if get_user_by_username(username):
        return jsonify({"message": "Ce nom d'utilisateur existe déjà."}), 409

    if add_user(username, password):
        return jsonify({"message": "Inscription réussie."}), 201
    else:
        return jsonify({"message": "Erreur interne."}), 500


@auth_app.route('/auth/login', methods=['POST'])
def login():
    """Connexion utilisateur, génération access + refresh token"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user_record = get_user_by_username(username)
    if user_record and check_password(user_record['password_hash'], password):
        # Access token (30 min)
        access_header = {"alg": "HS256"}
        access_payload = {
            "user": username,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
        }
        access_token = jwt.encode(access_header, access_payload, auth_app.config['SECRET_KEY']).decode()

        # Refresh token (7 jours)
        refresh_header = {"alg": "HS256"}
        refresh_payload = {
            "user": username,
            "type": "refresh",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        refresh_token = jwt.encode(refresh_header, refresh_payload, auth_app.config['SECRET_KEY']).decode()

        # Stockage en base
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO refresh_tokens (username, token, expires_at)
            VALUES (?, ?, ?)
        """, (username, refresh_token, str(datetime.now(timezone.utc) + timedelta(days=7))))
        conn.commit()
        conn.close()

        return jsonify({
            "message": "Connexion réussie.",
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 200

    return jsonify({"message": "Identifiants incorrects."}), 401


# ================================
#  ROUTES PROTÉGÉES
# ================================

@auth_app.route('/auth/validate', methods=['POST'])
@require_auth
def validate_token(payload):
    """Validation JWT (pour API Gateway)"""
    return jsonify({
        "message": "Token valide",
        "user": payload["user"]
    }), 200

@auth_app.route('/auth/refresh', methods=['POST'])
def refresh_token():
    """Rafraîchissement du token JWT"""
    data = request.get_json() or {}
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        return jsonify({"message": "Refresh token manquant"}), 400

    # Décodage et validation du refresh token
    try:
        decoded = jwt.decode(refresh_token, auth_app.config['SECRET_KEY'])
    except JoseError:
        return jsonify({"message": "Refresh token invalide ou expiré"}), 401

    if decoded.get("type") != "refresh" or "user" not in decoded:
        return jsonify({"message": "Refresh token invalide"}), 401

    username = decoded["user"]

    # Vérification en base que le refresh token existe pour cet utilisateur
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM refresh_tokens WHERE username = ? AND token = ?", (username, refresh_token))
    record = cursor.fetchone()
    conn.close()

    if not record:
        return jsonify({"message": "Refresh token inconnu"}), 401

    # Vérification d'expiration (optionnelle, prudente)
    exp = decoded.get("exp")
    if exp and int(datetime.now(timezone.utc).timestamp()) > int(exp):
        # supprimer le token expiré de la base
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM refresh_tokens WHERE token = ?", (refresh_token,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Refresh token expiré"}), 401

    # Génération d'un nouvel access token (30 minutes)
    new_header = {"alg": "HS256"}
    new_payload = {
        "user": username,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
    }
    new_access_token = jwt.encode(new_header, new_payload, auth_app.config['SECRET_KEY']).decode()

    return jsonify({"access_token": new_access_token}), 200


@auth_app.route('/auth/logout', methods=['POST'])
@require_auth
def logout(payload):
    """Déconnexion utilisateur"""
    data = request.get_json()
    refresh_token = data.get("refresh_token")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM refresh_tokens WHERE token = ?", (refresh_token,))
    conn.commit()
    conn.close()

    return jsonify({"message": f"Utilisateur {payload['user']} déconnecté avec succès."}), 200


# --- Lancement du service ---
if __name__ == '__main__':
    auth_app.run(debug=True, port=5002)
