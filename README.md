# 🧩 **Projet Microservices – Flask, JWT, API Gateway & Circuit Breaker**

Ce projet illustre une architecture microservices simple composée de :

* **Un Auth Service** (port 5002)
  → Gestion des utilisateurs, hash des mots de passe, génération et validation de JWT

* **Un Orders Service** (port 5001)
  → Réception et traitement des commandes, simulation de paiement

* **Un API Gateway** (port 5003)
  → Point d’entrée unique, vérification du JWT auprès du Auth Service

* **Une Interface Utilisateur / Front Flask** (port 5000)
  → Login, affichage des articles, passage de commande

L’objectif est de comprendre l’authentification via **JWT**, la communication entre microservices et l’usage d’un **Circuit Breaker** (pybreaker) pour gérer les pannes simulées du service de paiement.

---

## 📌 **Fonctionnalités**

### 🔐 Authentification (Auth Service)

* Inscription d’un utilisateur
* Connexion sécurisée
* Hash des mots de passe avec **Flask-Bcrypt**
* Génération de **JWT** valables 1 heure
* Endpoint de validation du token

### 🚪 API Gateway

* Filtre toutes les requêtes vers le Orders Service
* Vérifie le JWT via `/auth/validate`
* Enrichit les requêtes avec le nom d’utilisateur
* Gère les erreurs (token invalide, expiré, service indisponible…)

### 🛒 Orders Service

* Reçoit les commandes validées par le Gateway
* Simule un paiement : réussite 50% du temps
* Enregistre les commandes dans un fichier JSON
* Retourne un statut : `ok`, `error`, ou `error_service`

### 🖥️ Interface utilisateur (Front Flask)

* Page de login / inscription
* Affichage du panier d’articles
* Bouton “Acheter le panier”
* Affichage du résultat du paiement
* Possibilité de revenir à la page d’accueil

---

## 🗂️ **Structure du projet**

```
microservices-project/
│
├── app/                    # Application front Flask (port 5000)
│   ├── templates/          # HTML (login, accueil, achat)
│   ├── static/             # fichiers CSS/JS si nécessaire
│   ├── views.py            # routes Flask
│   └── __init__.py
│
├── auth_service.py         # Auth microservice (port 5002)
├── orders_service.py       # Orders microservice (port 5001)
├── gateway.py              # API Gateway (port 5003)
│
├── users.db                # Base SQLite pour Auth (auto-générée)
├── orders.json             # Fichier des commandes (auto-généré)
│
├── requirements.txt        # dépendances Python
└── README.md               # ce fichier
```

---

## ▶️ **Installation**

1. Cloner le projet :

```bash
git clone https://github.com/HelloDitE/MicroservicesElodieEloire.git
cd C:\Micorservices
```

2. Créer un environnement virtuel :

```bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
```

3. Installer les dépendances :

```bash
pip install -r requirements.txt
```

---

## 🚀 **Lancement des services**

Chaque microservice doit tourner dans un terminal séparé.

### 1️⃣ Auth Service (JWT)

```bash
python auth_service.py
```

→ Démarre sur **[http://127.0.0.1:5002](http://127.0.0.1:5002)**

### 2️⃣ Orders Service

```bash
python orders_service.py
```

→ Démarre sur **[http://127.0.0.1:5001](http://127.0.0.1:5001)**

### 3️⃣ API Gateway

```bash
python gateway.py
```

→ Démarre sur **[http://127.0.0.1:5003](http://127.0.0.1:5003)**

### 4️⃣ Front Flask (UI)

```bash
python run.py
```

→ Disponible sur **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔄 **Cycle d’utilisation**

1️⃣ L’utilisateur se connecte sur `http://localhost:5000/login`
2️⃣ Le front envoie la requête au **Auth Service**
3️⃣ Le Auth renvoie un **JWT** au front
4️⃣ L’utilisateur choisit des produits et clique sur “Acheter le panier”
5️⃣ Le front envoie la requête au **Gateway** avec :

```
Authorization: Bearer <token>
```

6️⃣ Le Gateway valide le token puis envoie la commande au Orders Service
7️⃣ Le Orders simule :

* paiement OK
* ou échec
* ou panne (si circuit breaker activé)

8️⃣ Le résultat est affiché dans `achat.html`

---

## ⚡ **Circuit Breaker (pybreaker)**

Le Circuit Breaker permet de **simuler des pannes de la banque ou du Orders Service**.

* après plusieurs erreurs → circuit "ouvert"
* les requêtes sont bloquées temporairement
* le front affiche :

```
Service indisponible, veuillez réessayer plus tard.
```

C’est essentiel pour comprendre la résilience des microservices.

---

## 🧪 **Tests avec Postman ou Curl**

### Login :

```bash
curl -X POST http://localhost:5002/auth/login \
     -H "Content-Type: application/json" \
     -d "{\"username\":\"test\", \"password\":\"1234\"}"
```

### Appel protégé :

```bash
curl -X POST http://localhost:5003/api/orders \
     -H "Authorization: Bearer <TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"items": [{"article":"Fraises","quantity":2,"total_price":5.0}]}'
```

---

## 📌 **Technologies**

* **Python 3.10+**
* **Flask 3**
* **Requests**
* **JWT (PyJWT)**
* **Flask-Bcrypt**
* **PyBreaker**
* **SQLite**
* **HTML + Tailwind**

---

## 📚 **Objectifs pédagogiques**

* Comprendre une architecture microservices
* Sécuriser les APIs avec JWT
* Distinguer Login / Token / Validation
* Apprendre le rôle d’un API Gateway
* Apprendre à gérer les pannes (Circuit Breaker)
* Construire un front Flask minimal connecté à des microservices

---

## 🧑‍🏫 Contact / Auteur

Projet développé dans le cadre d’un TP Microservices.
Étudiante : **Elodie Eloire**
Encadrant : **M Souhihi**

