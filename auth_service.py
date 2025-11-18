"""
Ce fichier implémente un microservice d’authentification en Flask qui :
- gère l’inscription (/auth/register),
- gère la connexion et renvoie un JWT (/auth/login),
- valide un JWT (/auth/validate),
- gère un refresh token (/auth/refresh),
- stocke les utilisateurs et tokens dans SQLite.
"""

from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from authlib.jose import jwt, JoseError
import sqlite3
from flask_bcrypt import Bcrypt

# --- 1. Initialisation de l'API ---
auth_app = Flask(__name__)
auth_app.config['SECRET_KEY'] = 'SuperSecretKeyPourTP'  # Clé secrète Authlib
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
#  ROUTE : REGISTER
# ================================
@auth_app.route('/auth/register', methods=['POST'])
def register():
    """API pour créer un compte utilisateur."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if get_user_by_username(username):
        return jsonify({"message": "Ce nom d'utilisateur existe déjà."}), 409

    if add_user(username, password):
        return jsonify({"message": "Inscription réussie."}), 201
    else:
        return jsonify({"message": "Erreur interne."}), 500


# ================================
#  ROUTE : LOGIN (Access + Refresh Token)
# ================================
@auth_app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user_record = get_user_by_username(username)

    if user_record and check_password(user_record['password_hash'], password):

        # -------------------------------
        # Génération ACCESS TOKEN (Authlib)
        # -------------------------------
        access_header = {"alg": "HS256"}
        access_payload = {
            "user": username,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
        }

        access_token = jwt.encode(access_header, access_payload, auth_app.config['SECRET_KEY'])
        access_token = access_token.decode()  # Authlib retourne bytes

        # -------------------------------
        # Génération REFRESH TOKEN (Authlib)
        # -------------------------------
        refresh_header = {"alg": "HS256"}
        refresh_payload = {
            "user": username,
            "type": "refresh",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }

        refresh_token = jwt.encode(refresh_header, refresh_payload, auth_app.config['SECRET_KEY'])
        refresh_token = refresh_token.decode()

        # Enregistrer en base
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
#  ROUTE : VALIDATE (pour le Gateway)
# ================================
@auth_app.route('/auth/validate', methods=['POST'])
def validate_token():
    data = request.get_json()
    token = data.get('token')

    if not token:
        return jsonify({"message": "Token manquant."}), 400

    try:
        # Décodage Authlib
        payload = jwt.decode(token, auth_app.config['SECRET_KEY'])
        return jsonify({
            "message": "Token valide",
            "user": payload["user"]
        }), 200

    except JoseError:
        return jsonify({"message": "Token invalide ou expiré"}), 401


# ================================
#  ROUTE : REFRESH TOKEN
# ================================
@auth_app.route('/auth/refresh', methods=['POST'])
def refresh_token():
    data = request.get_json()
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"message": "Refresh token manquant"}), 400

    try:
        payload = jwt.decode(refresh_token, auth_app.config['SECRET_KEY'])

        if payload.get("type") != "refresh":
            return jsonify({"message": "Type de token invalide"}), 401

        username = payload["user"]

        # Vérification en base
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM refresh_tokens WHERE username = ? AND token = ?",
                       (username, refresh_token))
        record = cursor.fetchone()
        conn.close()

        if not record:
            return jsonify({"message": "Refresh token inconnu"}), 401

        # Nouveau Access Token
        new_header = {"alg": "HS256"}
        new_payload = {
            "user": username,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
        }

        new_access_token = jwt.encode(new_header, new_payload, auth_app.config['SECRET_KEY'])
        new_access_token = new_access_token.decode()

        return jsonify({"access_token": new_access_token}), 200

    except JoseError:
        return jsonify({"message": "Refresh token invalide ou expiré"}), 401


# ================================
#  ROUTE : LOGOUT
# ================================
@auth_app.route('/auth/logout', methods=['POST'])
def logout():
    data = request.get_json()
    refresh_token = data.get("refresh_token")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM refresh_tokens WHERE token = ?", (refresh_token,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Déconnecté avec succès"}), 200


# --- Lancement du service ---
if __name__ == '__main__':
    auth_app.run(debug=True, port=5002)
