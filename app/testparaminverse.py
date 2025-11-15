from app import app
from flask import render_template
@app.route('/')
def index():
    user={'name':'john','surname':'doe'}
    return render_template('index.html', title='MDM', utilisateur=user)