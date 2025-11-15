from flask import Flask, jsonify, request
from flask import render_template
app = Flask(__name__)

@app.route('/api/salutation', methods=['GET'])
def salutation():
    return jsonify(message="Bonjour, bienvenue dans notre API de microservices !")



# Exemple d'ajout d'un utilisateur avec la méthode GET
@app.route('/api/utilisateurs', methods=['GET'])
def ajouter_utilisateur():
    data = request.args
    nom = data.get('nom')
    return jsonify(message=f"Utilisateur {nom} ajouté avec succès!"), 201 #201 est le code pour "Created"

# Exemple d'ajout d'un utilisateur avec la méthode POST
@app.route('/api/utilisateurs', methods=['POST'])
def ajouter_utilisateur():
    data = request.get_json()
    nom = data.get('nom')
    return jsonify(message=f"Utilisateur {nom} ajouté avec succès!"), 201

@app.route('/')
def index():
    # Affiche la page HTML avec le formulaire
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)