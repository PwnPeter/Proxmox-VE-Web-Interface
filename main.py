from flask import Flask, jsonify, render_template, request, Response
from werkzeug.utils import secure_filename
import csv
from tinydb import TinyDB, Query
from datetime import datetime

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # Max 2 Mo les fichiers

db = TinyDB("database/proxmox-class.json", indent=3)


os_equivalent = {
    "1": "CentOs",
    "2": "Debian",
    "3": "Linux_Autre",
    "4": "WinXP",
    "5": "Win7",
    "6": "Win10",
    "7": "WinSRV2016",
    "8": "WinSRV2019",
    "9": "Win_Autre",
}

classe_equivalent = {
    "1": "Ing1",
    "2": "Ing2",
    "3": "IR3",
    "4": "IR4",
    "5": "IR5",
    "6": "Bachelor",
    "7": "M1",
    "8": "M2",
    "9": "Autre",
}

ALLOWED_EXTENSIONS = {"csv"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    """page d'accueil du site"""

    liste_classes = []

    for table in db.tables():
        for row in db.table(table).all():
            liste_classes.append(
                {
                    "classe": classe_equivalent[row["classe"]],
                    "date_crea": row["date"].split(".")[0],
                    "os": [os_name for os_id, os_name in os_equivalent.items() if os_name.lower() == table.split("-")[::-1][0].lower()][0],
                }
            )
            break

    return render_template("index.html", liste_classes=liste_classes)


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """dashboard du site"""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_csv():
    """récupère le csv et les choix de génération des VM (classe + os)"""

    # check if the post request has the file part

    if "file" not in request.files or "os" not in request.form:
        print("pas de file ou de numero")
        return Response(status=404)

    file = request.files["file"]

    # if user does not select file, browser also
    # submit an empty part without filename

    print(file.filename)
    if file.filename == "":
        print("non du fichier vide")

        return Response(status=404)

    if file and allowed_file(file.filename):
        filename = secure_filename(
            file.filename
        )  # remove directory traversing, encoded caracters, space etc

    os = request.form["os"]

    # Do Upload csv to db + clone VM

    csv_file_string = file.read().decode()

    reader = csv.DictReader(
        csv_file_string.splitlines(),
        fieldnames=["firstname", "lastname", "email", "classe"],
        delimiter=";",
    )

    # print(ligne := str([ligne for num_ligne, ligne in enumerate(reader) if num_ligne == 1][0]["classe"]))
    print(not request.form["class"])
    print(not str(request.form["class"]) == "default")
    if not request.form["class"] or str(request.form["class"]) == "default":
        for num_ligne, ligne in enumerate(reader):
            if num_ligne == 1:
                classe = ligne["classe"]
    else:
        classe = str(request.form["class"])


    print(
        nom_table := f"classe-{classe_equivalent[classe]}-os-{os_equivalent[os]}".lower()
    )

    if nom_table in db.tables():
        return Response(status=409)

    table_promo = db.table(nom_table)

    reader = csv.DictReader(
        csv_file_string.splitlines(),
        fieldnames=["firstname", "lastname", "email", "classe"],
        delimiter=";",
    )

    next(reader, None)

    for rowrow in reader:
        rowrow = dict(rowrow)
        rowrow["date"] = str(datetime.now())
        table_promo.insert(rowrow)

    return jsonify({
                    "classe": classe_equivalent[classe],
                    "date_crea": rowrow["date"].split(".")[0],
                    "os": os_equivalent[os],
                }), 201


@app.route("/delete", methods=["PUT"])
def delete_class():
    """récupère la classe et l'os et supprime les VM"""
    return "cc"


app.run(debug=True, port=8080)
