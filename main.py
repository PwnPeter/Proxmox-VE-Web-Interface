from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 # Max 2 Mo les fichiers


ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    
    # check if the post request has the file part
    if 'file' not in request.files:
        print(1)
        return 404
        
    file = request.files['file']

    # if user does not select file, browser also
    # submit an empty part without filename

    print(file.filename)
    if file.filename == '':
        print(2)
        return 404


    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)   # remove directory traversing, encoded caracters, space etc

        print(file.read().decode())

    return 200

@app.route('/delete', methods=['PUT'])
def delete_class():
    """récupère la classe et l'os et supprime les VM""" 
    return 'cc'



app.run(debug=True, port=8080)