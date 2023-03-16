import requests
import shutil
import itertools
import re
import os
import csv
import glob
import pathlib
from flask_socketio import SocketIO
from datetime import datetime, timezone
from .forms import TemplateForm
from functools import wraps
from flask import (
    redirect,
    flash,
    request,
    render_template,
    session,
    make_response,
    url_for,
    g,
)
from werkzeug.utils import secure_filename
from app import app, forms

# Upload folder
UPLOAD_FOLDER = "/Users/normrasmussen/Documents/Projects/CSM_webapp/app/static/files/csv"
TEMPLATES_FOLDER = "/Users/normrasmussen/Documents/Projects/CSM_webapp/app/static/files/templates/"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["TEMPLATES_FOLDER"] = TEMPLATES_FOLDER
ALLOWED_EXTENSIONS = {"csv"}

# Global Variables
socketio = SocketIO(app)
specials = '"!@#$%^&[]*()-+?_=,<>/"'
url = "https://api.northpass.com/"


def download_csv():
    if request.method == "GET":
        download = make_response(session["dfcsv"])
        download.headers["Content-Disposition"] = "attachment; filename=export.csv"
        download.headers["Content-Type"] = "text/csv"
        return download


def key_response(response):
    if "402" in str(response):
        error = response.text
        return render_template("index.html", title="Error Home", error=error)
    if "401" in str(response):
        error = "Unauthorized access error.(401)"
        return render_template("index.html", title="Error Home", error=error)
    return correct_key(response)


def correct_key(response):
    data = response.json()
    session["school"] = data["data"]["attributes"]["properties"]["name"]
    return render_template("home.html", title="Active Session")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def key_required(check):
    @wraps(check)
    def decorated_function(*args, **kwargs):
        if session.get("key") is None:
            return redirect("/", code=302)
        return check(*args, **kwargs)

    return decorated_function


@app.route("/", methods=["GET", "POST"])
def ask_key():
    """This is the main function that asks for the API Key.
    Without this key, no other functions will work.
    It also assigns the api key to the session and clears the session upon each reload.
    """
    if request.method == "POST":
        session["key"] = request.form.get("apikey")
        if any(char in specials for char in session["key"]) or re.search(
            r"[\s]", session["key"]
        ):
            error = "Invalid Key."
            session.clear()
            return render_template("index.html", title="Home", error=error)
        if session["key"] is not None and len(session["key"]) > 10:
            endpoint = "/v2/properties/school"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url + endpoint, headers=headers)
            return key_response(response)
        error = "Hm. That doesn't seem right"
        session.clear()
        return render_template("index.html", title="Home", error=error)
    session.clear()
    return render_template("index.html", title="Home")


@app.route("/render_home", methods=["GET", "POST"])
@key_required
def render_home():
    if session.get("key"):
        return render_template("home.html", title="Home")
    return render_template("home.html", title="Enter Key")


@app.route("/clear_session", methods=["GET", "POST"])
def clear_session():
    if session.get("key"):
        if session.get("client_path"):
            client = session["client_path"]
            print(client)
            wildcard = glob.glob(client + '_*')
            print(wildcard)
            for directory in wildcard:
                print(directory)
                try:
                    shutil.rmtree(directory)
                    print(directory)
                except OSError:
                    print(OSError)
                    print("Error?")
        session.clear()
        error = "Session Cleared!"
        return render_template("index.html", error=error, title="Home, New session")
    return render_template("index.html", title="Home, New session")


@app.route("/table")
def table():
    return render_template("table.html", tables=[session["table"]], titles=["Table"])


@app.route("/upload_file", methods=["GET", "POST"])
@key_required
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file found or uploaded")
            return redirect(url_for("bulk_add_opts"))
        file = request.files["file"]
        if file.filename == "":
            print("no file exists")
            flash("No file found or uploaded")
            return redirect(url_for("home"))
        # return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            session["file"] = filename
            session["filepath"] = file_path
            file.save(file_path)
            file = list(csv.reader(open(file_path, "r")))
            return divide_values(file)
    return render_template("home.html", title="Bulk Add")


def divide_values(file):
    emails = []
    groups = []
    selection = request.form.get("learner-groups")
    if request.form["submit"]:
        if selection == "all-groups":
            for item in file[1:]:
                emails.append(item[0])
                groups.append(item[1:])
                # FEAT: These two extract the groups and emails into two lists
            groups = [item for group in groups for item in group]
            groups = list(set(groups))
            return api_csv_parse(emails, groups)
            # We're good here. This can now be sent to the api
            # functions with emails and groups.
        elif selection == "some-groups":
            submissions = []
            for item in file[1:]:
                # FEAT: This extracts each row as a list. Perfect for Learners in Specific Groups.
                submissions.append(item)
            for item in submissions:
                emails.append(item[0])
                print(type(emails))
                groups = item[1:]
                return api_csv_parse(emails, groups)
            return emails

    if request.form["preview"]:
        error = "Preview Button Still Under Construction. Try again later."
        return render_template("bulk_add.html", error=error, title="Preview Not Yet")

    return render_template("bulk_add.html", title="Uploaded File")


def api_csv_parse(emails, groups):
    if emails and groups:
        return api_add_ppl_groups(emails, groups)
    elif emails:
        return api_add_ppl(emails)
    elif groups:
        return api_add_groups(groups)
    return render_template("bulk_add.html", title="CSV Submission")


@app.route("/bulk_add_opts", methods=["GET", "POST"])
@key_required
def bulk_add_opts():
    return render_template("bulk_add.html", titles="Bulk Add Options")


@app.route("/bulk_add", methods=["GET", "POST"])
@key_required
def bulk_add():
    if request.method == "POST":
        emails = request.form.get("emails")
        groups = request.form.get("groups")
        if emails:
            if "\n" in emails:
                emails = emails.split("\n")
                emails = [email.strip() for email in emails]
                emails = [re.sub(r"[,]", "", email) for email in emails]
            elif "," in emails:
                emails = emails.split(",")
                emails = [email.strip() for email in emails]
            else:
                emails = emails.split()

        if groups:
            if "\n" in groups:
                groups = groups.split("\n")
                groups = [group.strip() for group in groups]
                groups = [re.sub(r"[,]", "", group) for group in groups]
            elif "," in groups:
                groups = groups.split(",")
                groups = [group.strip() for group in groups]
            else:
                groups = groups.split()

        if emails and groups:
            return api_add_ppl_groups(emails, groups)
        elif emails:
            return api_add_ppl(emails)
        elif groups:
            return api_add_groups(groups)
    return render_template("bulk_add.html")


def api_add_ppl(emails):
    payload2 = []
    endpoint = "v2/bulk/people"
    for email in emails:
        payload2.append({"email": email})
    payload = {"data": {"attributes": {"people": payload2}}}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Key": session["key"],
    }
    return payload
    # response = requests.post(url + endpoint, json=payload, headers=headers)
    # return check_response(response)


def api_add_groups(groups):
    payload2 = []
    endpoint = "v2/bulk/people"
    for group in groups:
        payload2.append({"groups": group})
    payload = {"data": {"attributes": {"people": payload2}}}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Key": session["key"],
    }
    return payload
    # response = requests.post(url + endpoint, json=payload, headers=headers)
    # return check_response(response)


def api_add_ppl_groups(emails, groups):
    payload2 = []
    endpoint = "v2/bulk/people"
    combinations = list(itertools.product(emails, groups))
    for combo in combinations:
        payload2.append({"email": combo[0], "groups": combo[1]})
    payload = {"data": {"attributes": {"people": payload2}}}

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Key": session["key"],
    }
    return payload
    # response = requests.post(url + endpoint, json=payload, headers=headers)
    # return check_response(response)


def check_response(response):
    response = str(response)
    if "202" in response:
        error = "Success! People have been added successfully."
        return render_template("bulk_add.html", title="People Added", error=error)
    elif "403" in response:
        error = "Uh oh. Looks like you don't have appropriate privileges."
        return render_template("bulk_add.html", error=error)
    elif "422" in response:
        error = "Hm. Looks like something was wrong with the data you added."
        return render_template("bulk_add.html", error=error)
    else:
        error = "Something went wrong, but I'm not sure what."
        return render_template("bulk_add.html", title="Shrug", error=error)


@app.route("/load_templates", methods=["GET", "POST"])
@key_required
def load_templates():
    count = 0
    templates = []

    while True:
        count += 1
        endpoint = "v2/custom_templates"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Api-Key": session["key"],
        }
        response = requests.get(url + endpoint, headers=headers)
        data = response.json()
        nextlink = data["links"]
        for response in data["data"]:
            last_updated = response["attributes"]["updated_at"].split("T")
            full_updated = response["attributes"]["updated_at"]
            g.full_updated = datetime.fromisoformat(full_updated)
            last_updated = last_updated[0]
            name, body, last_updated = (
                response["attributes"]["name"],
                response["attributes"]["body"],
                last_updated,
            )
            templates.append((name, body, last_updated))

        if "next" not in nextlink:
            break

        save_templates_backup(templates)
        return render_template(
            "templates.html",
            title="Templates",
            templates=templates,
        )

    return render_template("options.html")


@app.route("/templates", methods=["GET", "POST"])
@key_required
def templates():
    if request.method == "POST":
        if request.form["submit-template"]:
            name = request.form.get("template_name")
            body = request.form.get("body")
            if body == "":
                error = (
                    "Ooph. Looks like you didn't load the changes before submitting."
                )
                return render_template("templates.html", error=error)
            else:
                endpoint = "v2/custom_templates"
                headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "X-Api-Key": session["key"],
                }
                payload = {"custom_template": {"name": name, "body": body}}
                response = requests.post(url + endpoint, json=payload, headers=headers)
                return check_templates(response, name)
    return load_templates()


def check_templates(response, name):
    response = str(response)
    if "201" in response:
        error = (
            f"Success! The {name} template was successfully uploaded for "
            + session["school"]
            + "."
        )
        button = "Undo"
        return render_template(
            "templates.html", title="Templates Added", error=error, button=button
        )
    elif "403" in response:
        error = "Uh oh. Looks like you don't have appropriate privileges."
        return render_template("templates.html", error=error)
    elif "404" in response:
        error = "Hm. Looks like something was wrong in the templates."
        return render_template("templates.html", error=error)
    else:
        error = "Something went wrong, but I'm not sure what."
        return render_template("templates.html", title="Shrug", error=error)


def save_templates_backup(templates):
    session["client_path"] = os.path.join(TEMPLATES_FOLDER, session["school"])
    if any(char in specials for char in session["client_path"]):
        for char in specials:
            session["sanitized_path"] = session["client_path"].replace(char,"")
            print(session["sanitized_path"])
    else:
        session["sanitized_path"] = session["client_path"]
    print(session["client_path"])
    today = datetime.now(timezone.utc)
    if os.path.exists(session["client_path"]):
        pass
    else:
        path = session["client_path"] + "_" + str(today)
        os.mkdir(path)

    for tupe in templates:
        file_name = tupe[0] + ".liquid"
        file_body = tupe[1]
        complete_path = os.path.join(path, file_name)

        with open(complete_path, "w+") as temp:
            temp.write(file_body)
            temp.close


@app.route("/undo_template", methods=["POST"])
@key_required
def undo_template():
    if request.method == "POST":
        if request.form["undo_templates"]:
            pass

@socketio.on("disconnect")
def test_disconnect():
    print("Client disconnected")


@socketio.on("connect")
def test_connect():
    print("connection established")


@app.route("/cmtest", methods=["GET", "POST"])
def cmtest():
    form = TemplateForm()
    if form.validate_on_submit():
        text = form.template_code.data
    return render_template("templates.html", form=form)


app.secret_key = "@&I\x1a?\xce\x94\xbb0w\x17\xbf&Y\xa2\xc2(A\xf5\xf2\x97\xba\xeb\xfa"


# if __name__ == "__main__":
#    ask_key()
