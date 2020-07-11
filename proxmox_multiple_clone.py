#/usr/bin/python3

import csv
import json
import time
from datetime import datetime
from random import randint
from threading import Thread

import requests
import logging

from flask import Flask, Response, jsonify, render_template, request
from flask_basicauth import BasicAuth
from tinydb import Query, TinyDB, where
from werkzeug.utils import secure_filename


app = Flask(__name__)
r = requests.Session()
basic_auth = BasicAuth(app)
db = TinyDB("database/proxmox-class.json", indent=3)
requests.urllib3.disable_warnings()


app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # Max 2 Mo les fichiers

app.config["FLASK_SECRET"] = "jksfd$*^^$*ù!fsfshjkhfgks" # clé pour chiffrer les cookies/session etc

app.config["BASIC_AUTH_USERNAME"] = "admin" # login 

app.config["BASIC_AUTH_PASSWORD"] = "1234" # password


#infos proxmox
url_proxmox = "https://172.16.1.92:8006" #without / at the end
username = "projet1@pve"
password = "EsFJZ2409GYX@ip"

# Prints logger info to terminal
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Change  this to DEBUG if you want a lot more info
stream_handler = logging.StreamHandler()
file_handler = logging.FileHandler("logs/server.log", encoding="utf-8")
# create formatter
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s - line %(lineno)d"
)

# add formatter to stream_handler
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
# http_handler.setFormatter(formatter_http)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)
# logger.addHandler(http_handler)

nodes_list = ["proxmox1"]  # , "proxmox2"]
# remettre proxmox2 quand les templates auront été créé dessus

role = "Etudiant"
authentication_mode = "authentification-AD"

os_equivalent = {
    "1": "CentOS",
    "2": "Debian",
    "3": "Linux_Autre",
    "4": "WinXP",
    "5": "Win7",
    "6": "Win10",
    "7": "WinSRV2016",
    "8": "WinSRV2019",
    "9": "Win_Autre",
}

template_equivalent = {
    "CentOS": 100,
    "WinSRV2016": 104,
}

class_equivalent = {
    "1": "ING1",
    "2": "ING2",
    "3": "IR3",
    "4": "IR4",
    "5": "IR5",
    "6": "Bachelor",
    "7": "M1",
    "8": "M2",
    "9": "Autre",
}

ALLOWED_EXTENSIONS = {"csv"} #extensions autorisées


############################################################################
############################################################################
############################################################################


def login_proxmox():
    """se connecte au proxmox via l'API et récupère les infos de session"""
    response_prox = r.post(
        url_proxmox + "/api2/json/access/ticket",
        verify=False,
        params={"username": username, "password": password},
    ).json()

    logger.info(response_prox)

    return response_prox["data"]["ticket"], response_prox["data"]["CSRFPreventionToken"]


def get_storage(ticket, csrftoken, classe):
    """retourne ne storage associé à la classe (permet d'éviter les problèmes de case"""
    storage_list = []
    for node in nodes_list:
        response_prox = r.get(
            url_proxmox + f"/api2/json/nodes/{node}/storage",
            verify=False,
            cookies={"PVEAuthCookie": ticket},
            headers={"CSRFPreventionToken": csrftoken},
        ).json()
        for storage in response_prox["data"]:
            if storage["storage"].lower() == classe.lower():

                return storage["storage"]


def get_vm_status(ticket, csrftoken, node, id_vm):
    """recupère le statut de la VM dans le node choisi"""
    while 1:
        try:
            response_prox = r.get(
                url_proxmox + f"/api2/json/nodes/{node}/qemu/{id_vm}/status/current",
                verify=False,
                cookies={"PVEAuthCookie": ticket},
                headers={"CSRFPreventionToken": csrftoken},
            )
            # print(response_prox.status_code)
            # print(response_prox.text)
            break
        except:
            continue
    return response_prox


def request_clone_vm(
    ticket, csrftoken, student, vm_name, storage, nom_table, node, clone_os):
    """requêtes qui vont cloner les VM"""
    logger.info(f"Starting the VM clone {nom_table} for {student['email']} VM: {student['id_vm']}")
    while 1:
        try:
            response_prox = r.post(
                url_proxmox + f"/api2/json/nodes/{node}/qemu/{clone_os}/clone",
                verify=False,
                params={
                    "newid": int(student["id_vm"]),
                    "name": vm_name,
                    "full": 1,
                    "storage": f"{storage}",
                },
                cookies={"PVEAuthCookie": ticket},
                headers={"CSRFPreventionToken": csrftoken},
            )

            if response_prox.status_code == 200:
                break
            elif response_prox.status_code == 500:
                logging.warning(f"{student['id_vm']} ({vm_name}) already exsits")
                break
            else:
                logging.warning(
                    f"restart clone {vm_name} {response_prox.status_code} {response_prox.text}"
                )
                time.sleep(randint(5, 15))
                continue
        except:
            time.sleep(randint(5, 15))
            continue

    if response_prox.status_code == 200 or response_prox.status_code == 500:
        table_db = db.table(nom_table)

        response_name = ""

        is_cloned = ""
        while is_cloned != vm_name:
            is_cloned = get_vm_status(ticket, csrftoken, node, student["id_vm"])
            is_cloned = is_cloned.json()["data"]["name"]
            time.sleep(randint(5, 15))

        logger.info(
            f"VM: {student['id_vm']} OS: {clone_os}, User: {student['email']} cloned"
        )

        i = 1
        while i < 3:
            response_prox = r.put(
                url_proxmox + f"/api2/json/access/acl",
                verify=False,
                params={
                    "path": f"/vms/{student['id_vm']}",
                    "users": f"{student['email'].split('@')[0]}@{authentication_mode}",
                    "roles": role,
                },
                cookies={"PVEAuthCookie": ticket},
                headers={"CSRFPreventionToken": csrftoken},
            )

            if response_prox.status_code == 200:

                logger.info(
                    f"VM: {student['id_vm']} OS: {clone_os}, User: {student['email']} right set"
                )
                table_db.update({"is_cloned": True}, where("id_vm") == student["id_vm"])
                break

            time.sleep(randint(5, 15))
            i += 1

        if response_prox.status_code != 200:
            logger.error(
                f"VM: {student['id_vm']} OS: {clone_os}, User: {student['email']} right not set"
            )


def clone_vm(nom_table):
    """initialisation du clone des VM à partir du template associé"""
    ticket, csrftoken = login_proxmox()

    classe = [
        classe_name
        for classe_id, classe_name in class_equivalent.items()
        if classe_name.lower() == nom_table.split("-")[1].lower()
    ][0].lower()

    storage = get_storage(ticket, csrftoken, classe)

    os_name = [
        os_name
        for os_id, os_name in os_equivalent.items()
        if os_name.lower() == nom_table.split("-")[::-1][0].lower()
    ][0]
    clone_os = template_equivalent[os_name]
    # print(f"Os name : {os_name}, Id vm {clone_os}")

    # nodes_list_for_cloning = get_last_vm_id(ticket, csrf)

    threads = []

    for pos, student in enumerate(db.table(nom_table).all()):

        if int(student["id_vm"]) % 2 == 0 and len(nodes_list) > 1:
            node = nodes_list[1]  # si pair ça go sur proxmox2
        else:
            node = nodes_list[0]  # sinon proxmox1

        # print(f"Node {node}")

        vm_name = f"{os_name}-{student['email']}".split("@")[0]

        t = Thread(
            name=f"Clone {vm_name}",
            target=request_clone_vm,
            args=[
                ticket,
                csrftoken,
                student,
                vm_name,
                storage,
                nom_table,
                node,
                clone_os,
            ],
        )
        threads.append(t)
        t.start()
        time.sleep(0.5)

    [thread.join() for thread in threads]

    logger.info("Threads clone finished")


def request_delete_vm(ticket, csrftoken, node, student):
    """requêtes qui vont stopper et supprimer les threads"""
    logger.info(f"Starting VM removal {student['id_vm']} of {student['email']}")

    while 1:
        try:
            response_prox = r.post(
                url_proxmox
                + f"/api2/json/nodes/{node}/qemu/{student['id_vm']}/status/stop",
                verify=False,
                params={"timeout": 5},
                cookies={"PVEAuthCookie": ticket},
                headers={"CSRFPreventionToken": csrftoken},
            )

            if response_prox.status_code == 200:
                break
            elif response_prox.status_code == 500:
                logger.warning(f"Doesn't exist")
                break
            else:
                logger.warning(
                    f"Restart delete {student['id_vm']} {response_prox.status_code} {response_prox.text}"
                )
                time.sleep(randint(5, 15))
                continue

        except:
            time.sleep(randint(5, 15))
            continue

    if response_prox.status_code == 200:
        # print(response_prox.text)

        is_stopped = ""

        while is_stopped != "stopped":
            is_stopped = get_vm_status(ticket, csrftoken, node, student["id_vm"])
            is_stopped = is_stopped.json()["data"]["qmpstatus"]
            time.sleep(randint(5, 15))

        logger.info(f"VM {student['id_vm']} stopped")

        i = 1
        while i < 3:

            response_prox = r.delete(
                url_proxmox + f"/api2/json/nodes/{node}/qemu/{student['id_vm']}",
                verify=False,
                params={},
                cookies={"PVEAuthCookie": ticket},
                headers={"CSRFPreventionToken": csrftoken},
            )

            if response_prox.status_code == 200:

                logger.info(f"VM: {student['id_vm']}, User: {student['email']} deleted")
                # table_db.update({"is_cloned": False}, where('id_vm') == student['id_vm'])
                break

            time.sleep(randint(5, 15))
            i += 1

        if response_prox.status_code != 200:
            logger.error(
                f"VM: {student['id_vm']}, User: {student['email']} not deleted"
            )


def delete_vm(nom_table):
    """initialise les threads qui vont stopper et supprimer les vm"""
    ticket, csrftoken = login_proxmox()

    threads = []

    for pos, student in enumerate(db.table(nom_table).all()):
        if int(student["id_vm"]) % 2 == 0 and len(nodes_list) > 1:
            node = nodes_list[1]  # si pair ça go sur proxmox2
        else:
            node = nodes_list[0]  # sinon proxmox1

        # print(f"Node {node}")

        os_name = [
            os_name
            for os_id, os_name in os_equivalent.items()
            if os_name.lower() == nom_table.split("-")[::-1][0].lower()
        ][0]

        vm_name = f"{os_name}-{student['email']}".split("@")[0]

        t = Thread(
            name=f"Delete {vm_name}",
            target=request_delete_vm,
            args=[ticket, csrftoken, node, student],
        )
        threads.append(t)
        t.start()
        time.sleep(0.5)

    [thread.join() for thread in threads]

    logger.info("Threads delete finished")


def allowed_file(filename):
    """check si l'extension du fichier upload se termine bien par l'une des extension contenue dans la variable ALLOWED_HOST"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


############################################################################################################
############################################################################################################
############################################################################################################


@app.route("/", methods=["GET"])
@basic_auth.required
def index():
    """page d'accueil du site"""

    liste_classes_os = []

    for table in db.tables():
        for row in db.table(table).all():
            liste_classes_os.append(
                {
                    "classe": class_equivalent[row["classe"]],
                    "date_crea": row["date"].split(".")[0],
                    "os": os_equivalent[row["os"]],
                }
            )
            break

    return render_template(
        "index.html",
        liste_classes_os=liste_classes_os,
        liste_os=os_equivalent,
        liste_classes=class_equivalent,
        url_proxmox=url_proxmox,
        url_proxmox_troncat=url_proxmox.split("://")[1],
    )


@app.route("/details", methods=["GET"])
@basic_auth.required
def details():
    """details d'une classe-os du site"""
    classe = request.args.get("classe")
    os = request.args.get("os")

    table_promo = db.table(f"classe-{classe}-os-{os}".lower())

    return render_template(
        "details.html",
        liste_eleve=table_promo.all(),
        classe=classe,
        os=os,
        url_proxmox=url_proxmox,
        url_proxmox_troncat=url_proxmox.split("://")[1],
    )


# API REST

@app.route("/upload", methods=["POST"])
def upload_csv():
    """récupère le csv et les choix de génération des VM (classe + os)"""

    # check if the post request has the file part

    if "file" not in request.files or "os" not in request.form:
        logger.error("None File or empty os")
        return Response(status=404)

    file = request.files["file"]

    # if user does not select file, browser also
    # submit an empty part without filename

    if file.filename == "":
        logger.error("Empty file")

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

    if not request.form["class"] or str(request.form["class"]) == "default":
        for num_ligne, ligne in enumerate(reader):
            if num_ligne == 1:
                classe = ligne["classe"]
    else:
        classe = str(request.form["class"])

    nom_table = f"classe-{class_equivalent[classe]}-os-{os_equivalent[os]}".lower()

    if nom_table in db.tables():
        return Response(status=409)

    table_promo = db.table(nom_table)
    logger.info(f"Table {nom_table} created")

    reader = csv.DictReader(
        csv_file_string.splitlines(),
        fieldnames=["firstname", "lastname", "email", "classe"],
        delimiter=";",
    )

    next(reader, None)

    for pos, rowrow in enumerate(reader, start=1): # for each student, create entry in table
        rowrow = dict(rowrow)
        rowrow["date"] = str(datetime.now())
        rowrow["classe"] = classe
        rowrow["os"] = os
        rowrow["id_vm"] = f"{classe}{os}{pos:03d}"
        rowrow["is_cloned"] = False

        table_promo.insert(rowrow)

    logger.info(f"Table {nom_table} created and datas inserted")

    clone_vm(nom_table)

    return (
        jsonify(
            {
                "classe": class_equivalent[classe],
                "date_crea": rowrow["date"].split(".")[0],
                "os": os_equivalent[os],
            }
        ),
        201,
    )


@app.route("/delete", methods=["PUT"])
def delete_class():
    """récupère la classe et l'os et supprime les VM"""
    content = request.json
    delete_vm(f"classe-{content['classe']}-os-{content['os']}".lower())
    db.drop_table(f"classe-{content['classe']}-os-{content['os']}".lower())
    logger.info(f"Table classe-{content['classe'].lower()}-os-{content['os'].lower()} dropped")
    return "", 201


if __name__ == "__main__":

    app.run(debug=False, port=8080)
