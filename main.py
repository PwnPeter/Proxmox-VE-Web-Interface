from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    """page d'accueil du site"""
    return render_template("index.html")


@app.route('/dashboard', methods=['GET'])
def dashboard():
    """dashboard du site"""
    return render_template("index.html")


@app.route('/upload', methods=['POST'])
def upload_csv():
    """récupère le csv et les choix de génération des VM (classe + os)"""

    return 'cc'

@app.route('/delete', methods=['PUT'])
def delete_class():
    """récupère la classe et l'os et supprime les VM""" 
    return 'cc'



app.run(debug=True, port=8080)