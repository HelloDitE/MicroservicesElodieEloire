# app/views.py
from app import app
from flask import render_template, request, redirect, url_for, session
import requests

# ---------------------------
# CONFIGURATION DES SERVICES
# ---------------------------
GATEWAY_URL = "http://localhost:5003/api/orders"
AUTH_LOGIN_URL = "http://localhost:5002/auth/login"
AUTH_REGISTER_URL = "http://localhost:5002/auth/register"
AUTH_REFRESH_URL = "http://localhost:5002/auth/refresh"


# Clé secrète Flask pour la session (stockage temporaire du token)
app.secret_key = "SuperSecretKeyTP"


# ==========================
# 1️⃣ PAGE DE CONNEXION
# ==========================

#C’est la page de connexion et d’inscription.
#Elle envoie les identifiants au microservice Auth

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Page de login / inscription.
    Envoie les infos au microservice d'authentification.
    """
    if request.method == 'POST':
        username = request.form.get('user')
        password = request.form.get('password')
        action = request.form.get('action')

        if not username or not password:
            return render_template('login.html', error="Veuillez remplir tous les champs.")

        # --- INSCRIPTION ---
        if action == 'register':
            try:
                r = requests.post(AUTH_REGISTER_URL, json={'username': username, 'password': password})
                if r.status_code == 201:
                    msg = "✅ Inscription réussie. Connectez-vous maintenant."
                    return render_template('login.html', error=msg)
                else:
                    return render_template('login.html', error=r.json().get('message', 'Erreur d’inscription.'))
            except requests.exceptions.ConnectionError:
                return render_template('login.html', error="⚠️ Auth Service indisponible (port 5002).")

        # --- CONNEXION ---
        try:
            r = requests.post(AUTH_LOGIN_URL, json={'username': username, 'password': password})
            if r.status_code == 200:
                token = r.json().get('access_token')
                session['token'] = token  # stocke le JWT dans la session Flask
                session['refresh_token'] = r.json().get('refresh_token')
                session['user'] = username
                return redirect(url_for('accueil', user=username))
            else:
                return render_template('login.html', error="❌ Identifiants incorrects.")
        except requests.exceptions.ConnectionError:
            return render_template('login.html', error="⚠️ Auth Service indisponible (port 5002).")

    # --- GET : afficher la page ---
    return render_template('login.html')


# ==========================
# 2️⃣ PAGE D’ACCUEIL
# ==========================
@app.route('/accueil')
def accueil():
    """
    Page principale avec la liste des articles.
    """
    user = request.args.get('user') or session.get('user')
    token = session.get('token')

    if not user or not token:
        return redirect(url_for('login'))

    return render_template('accueil.html', user=user, token=token)


# ==========================
# 3️⃣ ENVOI DU PANIER
# ==========================

#lit le panier choisi
#construit la commande
#envoie la commande au Gateway
#récupère la réponse
#affiche le résultat de l’achat

@app.route('/submit_order/<user>', methods=['POST'])
def submit_order(user):
    """
    Envoie le panier au Gateway pour traitement via le microservice Orders.
    """
    token = request.form.get('user_token') or session.get('token')

    # --- 1. Construire la liste des articles sélectionnés ---
    articles = {
        'Fraises (barquette de 250g)': 2.50,
        'Haricots (kg)': 1.80,
        'Laine': 4.00,
        'Pêches (kg)': 3.00,
        'Pastèques': 4.00,
        'Paquet de pâtes': 1.20,
        'Cookies': 2.00
    }

    items = []
    for nom, prix in articles.items():
        qte = int(request.form.get(nom, 0))
        if qte > 0:
            items.append({
                'article': nom,
                'quantity': qte,
                'unit_price': prix,
                'total_price': round(prix * qte, 2)
            })

    if not items:
        return render_template('accueil.html', user=user, token=token,
                               error_message="Veuillez sélectionner au moins un article.")

    # --- 2. Appeler le Gateway ---
    try:
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        response = requests.post(GATEWAY_URL, json={'items': items}, headers=headers)

        # --- 3. Analyse de la réponse ---
        if response.status_code in (200, 201):
            try:
                data = response.json()
                # Si c’est une liste, on prend le premier élément
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
                elif not isinstance(data, dict):
                    data = {}

                status = data.get('status', 'ok')
            except Exception as e:
                print("Erreur de parsing JSON :", e)
                status = "error_internal"

            return render_template('achat.html', user=user, status=status, order_details=items)


        elif response.status_code == 401:
            # Tentative de refresh
            refresh_token = session.get('refresh_token')
            r = requests.post(AUTH_REFRESH_URL, json={'refresh_token': refresh_token})
            
            if r.status_code == 200:
                # Remplacer le token et réessayer
                new_token = r.json().get('access_token')
                session['token'] = new_token

                headers = {'Authorization': f'Bearer {new_token}'}
                response = requests.post(GATEWAY_URL, json={'items': items}, headers=headers)

                if response.status_code in (200, 201):
                    try:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            data = data[0]
                        elif not isinstance(data, dict):
                            data = {}

                        status = data.get('status', 'ok')
                    except Exception as e:
                        print("Erreur de parsing JSON après refresh :", e)
                        status = "error_internal"

                    return render_template('achat.html', user=user, status=status, order_details=items)

            else:
                return render_template('achat.html', user=user, status='error_auth')


        else:
            # Autre erreur (service down, etc.)
            return render_template('achat.html', user=user, status='error_service', order_details=items)

    except requests.exceptions.ConnectionError:
        # Si le Gateway ne répond pas
        return render_template('achat.html', user=user, status='error_service', order_details=items)


# ==========================
# 4️⃣ ROUTE PAR DÉFAUT
# ==========================
@app.route('/')
def index():
    """
    Redirection directe vers le login.
    """
    return redirect(url_for('login'))
