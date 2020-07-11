from flask import Flask, jsonify, render_template, request, Response
from werkzeug.utils import secure_filename
import csv
from tinydb import TinyDB, Query, where
from datetime import datetime
import requests
import json
import time
import asyncio
from threading import Thread

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # Max 2 Mo les fichiers

db = TinyDB("database/proxmox-class.json", indent=3)

r = requests.Session()

requests.urllib3.disable_warnings()

nodes_list = ["proxmox1"]#, "proxmox2"]

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

classe_equivalent = {
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

ALLOWED_EXTENSIONS = {"csv"}


def login_proxmox():
    response_prox = r.post(
        url_proxmox + "/api2/json/access/ticket",
        verify=False,
        params={"username": username, "password": password},
    ).json()

    print(response_prox)

    return response_prox["data"]["ticket"], response_prox["data"]["CSRFPreventionToken"]


# def get_last_vm_id(ticket, csrf):
#     start_nodes_list = []

#     for node in nodes_list:
#         response_prox = r.get(
#             url_proxmox + f"/api2/json/nodes/{node}/qemu",
#             verify=False,
#             cookies={"PVEAuthCookie": ticket},
#             headers={"CSRFPreventionToken": csrf},
#         ).json()
#         last_vmid = (
#             int(
#                 sorted(response_prox["data"], key=lambda i: i["vmid"], reverse=True)[0][
#                     "vmid"
#                 ]
#             )
#             + 1000
#         )  # on choppe la dernière vmid dispo et on ajoute +1000 pour commencer ici

#         start_nodes_list.append({"node": node, "last_vmid": last_vmid})

#     print(start_nodes_list)

#     return nodes_list

def get_storage(ticket, csrftoken, classe):
    storage_list =[]
    for node in nodes_list:
        response_prox = r.get(url_proxmox+f'/api2/json/nodes/{node}/storage', verify=False, cookies={'PVEAuthCookie':ticket}, headers={'CSRFPreventionToken':csrftoken}).json()
        for storage in response_prox["data"]:
            if storage["storage"].lower() == classe.lower():
               # print(r.get(url_proxmox+f'api2/json/nodes/{node}/storage/{storage["storage"]}', verify=False, cookies={'PVEAuthCookie':ticket}, headers={'CSRFPreventionToken':csrftoken}).json())
                
                return storage["storage"]


def get_vm_status(ticket, csrftoken, node, id_vm):
    while 1:
        try:
            response_prox = r.get(
                            url_proxmox + f"/api2/json/nodes/{node}/qemu/{id_vm}/status/current",
                            verify=False,
                            cookies={"PVEAuthCookie": ticket},
                            headers={"CSRFPreventionToken": csrftoken},
                        )
            break
        except:
            continue
    return response_prox.json()

def request_clone_vm(ticket, csrftoken, student, vm_name, storage, nom_table, node, clone_os):
    while 1:
        try:
            response_prox = r.post(
                    url_proxmox + f"/api2/json/nodes/{node}/qemu/{clone_os}/clone",
                    verify=False,
                    params={"newid": int(student["id_vm"]), "name":vm_name, "full":1, "storage":f"{storage}"},
                    cookies={"PVEAuthCookie": ticket},
                    headers={"CSRFPreventionToken": csrftoken},
                )

            break
        except:
            time.sleep(10)
            continue


    if response_prox.status_code == 200:
        table_db = db.table(nom_table)

        response_name = ""

        while get_vm_status(ticket, csrftoken, node, student["id_vm"])["data"]["name"] != vm_name:
            time.sleep(10)

        table_db.update({"is_cloned": True}, where('id_vm') == student['id_vm'])
        print(f"VM: {student['id_vm']} OS: {clone_os}, User: {student['email']} cloned")

        print(f"{student['email'].split('@')[0]}@authentification-AD")

        response_prox = r.put(
            url_proxmox + f"/api2/json/access/acl",
            verify=False,
            params={"path": f"/vms/{student['id_vm']}", "users":f"{student['email'].split('@')[0]}@authentification-AD", "roles":"Etudiant"},
            cookies={"PVEAuthCookie": ticket},
            headers={"CSRFPreventionToken": csrftoken},
            )

        print(response_prox.status_code)
        print(f"VM: {student['id_vm']} OS: {clone_os}, User: {student['email']} Right set")

        print("--------------------------\n")


def clone_vm(nom_table):
    ticket, csrftoken = login_proxmox()

    # recup=r.get(url_proxmox+'/api2/json/nodes/proxmox1/qemu/2045/status', verify=False, cookies={'PVEAuthCookie':ticket}, headers={'CSRFPreventionToken':csrftoken})
    # print(recup.status_code)
    # print(recup.text)
    classe = [classe_name for classe_id, classe_name in classe_equivalent.items() if classe_name.lower() == nom_table.split("-")[1].lower()][0].lower()

    print("classe : "+str(classe))

    storage = get_storage(ticket, csrftoken, classe)

    os_name = [os_name for os_id, os_name in os_equivalent.items() if os_name.lower() == nom_table.split("-")[::-1][0].lower()][0]
    clone_os = template_equivalent[os_name]
    print(f"Os name : {os_name}, Id vm {clone_os}")
    
    # nodes_list_for_cloning = get_last_vm_id(ticket, csrf)

    threads = []

    for pos, student in enumerate(db.table(nom_table).all()):
        if int(student["id_vm"]) % 2 == 0 and len(nodes_list)>1:
            node = nodes_list[1] #si pair ça go sur proxmox2
        else:
            node = nodes_list[0] #sinon proxmox1

        print(f"Node {node}")

        vm_name = f"{os_name}-{student['email']}".split("@")[0]

        t = Thread(name=f"Clone {vm_name}", target=request_clone_vm, args=[ticket, csrftoken, student, vm_name, storage, nom_table, node, clone_os])
        threads.append(t)
        t.start()
        time.sleep(1)

    [thread.join() for thread in threads]

    print("Threads finis")

def request_delete_vm(ticket, csrftoken, node, student):
    while 1:
        try:
            response_prox = r.post(
                        url_proxmox + f"/api2/json/nodes/{node}/qemu/{student['id_vm']}/status/stop",
                        verify=False,
                        params={"timeout":5},
                        cookies={"PVEAuthCookie": ticket},
                        headers={"CSRFPreventionToken": csrftoken},
                    )
            break

        except:
            time.sleep(10)
            continue

    if response_prox.status_code == 200:
        print(response_prox.text)

        while get_vm_status(ticket, csrftoken, node, student["id_vm"])["data"]["qmpstatus"] != "stopped":
            time.sleep(10)

        print(f"VM {student['id_vm']} stopped")

        response_prox = r.delete(
                url_proxmox + f"/api2/json/nodes/{node}/qemu/{student['id_vm']}",
                verify=False,
                params={},
                cookies={"PVEAuthCookie": ticket},
                headers={"CSRFPreventionToken": csrftoken},
            )

        print(response_prox.status_code)
        print(response_prox.text)



def delete_vm(nom_table):
    ticket, csrftoken = login_proxmox()


    threads = []

    for pos, student in enumerate(db.table(nom_table).all()):
        if int(student["id_vm"]) % 2 == 0 and len(nodes_list)>1:
            node = nodes_list[1] #si pair ça go sur proxmox2
        else:
            node = nodes_list[0] #sinon proxmox1

        print(f"Node {node}")

        os_name = [os_name for os_id, os_name in os_equivalent.items() if os_name.lower() == nom_table.split("-")[::-1][0].lower()][0]


        vm_name = f"{os_name}-{student['email']}".split("@")[0]

        t = Thread(name=f"Delete {vm_name}", target=request_delete_vm, args=[ticket, csrftoken, node, student])
        threads.append(t)
        t.start()
        time.sleep(1)

    [thread.join() for thread in threads]

    print("Threads finis")

        


        


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
                    "os": os_equivalent[row["os"]],
                }
            )
            break

    return render_template("index.html", liste_classes=liste_classes)


@app.route("/details", methods=["GET"])
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

    for pos, rowrow in enumerate(reader, start=1):
        rowrow = dict(rowrow)
        rowrow["date"] = str(datetime.now())
        rowrow["classe"] = classe
        rowrow["os"] = os
        rowrow["id_vm"] = f"{classe}{os}{pos:03d}"
        rowrow['is_cloned'] = False
        table_promo.insert(rowrow)

    clone_vm(nom_table)

    return (
        jsonify(
            {
                "classe": classe_equivalent[classe],
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
    print(content)
    response_del = delete_vm(f"classe-{content['classe']}-os-{content['os']}".lower())

    if response_del == 500:
        print("On envoie 500")
        return "", 500
    
    db.drop_table(f"classe-{content['classe']}-os-{content['os']}".lower())
    return "", 201


if __name__ == "__main__":
    url_proxmox = "https://172.16.1.92:8006"
    username = "projet1@pve"
    password = "EsFJZ2409GYX@ip"
    app.run(debug=True, port=8080)
