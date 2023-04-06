import requests
import shutil
import itertools
import re
import os
import csv
import glob
import time
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from functools import wraps
import flask
from flask import (
    redirect,
    flash,
    request,
    render_template,
    session,
    make_response,
    url_for,
    g,
    send_file,
)
from werkzeug.utils import secure_filename
from app import app

UPLOAD_FOLDER = (
    "/Users/normrasmussen/Documents/Projects/CSM_webapp/app/static/files/csv/"
)
TEMPLATES_FOLDER = (
    "/Users/normrasmussen/Documents/Projects/CSM_webapp/app/static/files/templates/"
)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["TEMPLATES_FOLDER"] = TEMPLATES_FOLDER
ALLOWED_EXTENSIONS = {"csv"}

app.config.update(SECRET_KEY=os.urandom(24))
app.permanent_session_lifetime = timedelta(minutes=30)


specials = '"!@#$%^&*()-+?_=,<>/"'
url = "https://api.northpass.com/"

@app.route("/downloadcsv", methods=["GET", "POST"])
def download_csv():
    if request.method == "GET":
        download = make_response(session["dfcsv"])
        download.headers["Content-Disposition"] = "attachment; filename=export.csv"
        download.headers["Content-Type"] = "text/csv"
        return download

@app.route("/send_to_admin")
def send_to_admin():
    if request.method == "GET":
        url = f"https://app.northpass.com/app/admin/{session['admin_id']}"
        return redirect(url)


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
    session["raw_school"] = data["data"]["attributes"]["properties"]["name"]
    session["sani_school"] = session["raw_school"].replace("[", "").replace("]", "")
    session["admin_id"] = data["data"]["id"]
    session["client_path"] = os.path.join(TEMPLATES_FOLDER, session["sani_school"])
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

def grab_subdomain():
    endpoint = "/v2/courses"
    headers = {"accept":"application/json", "X-Api-Key":session["key"]}
    response = requests.get(url+endpoint, headers=headers)
    data2 =  response.json()["data"][0]["links"]["enroll"]["href"]
    data = urlparse(data2)
    data = str("https://" + data.netloc)
    print(data)
    session["subdomain"] = data


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
            grab_subdomain()
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
        print("key exists")
        print(session["key"])
        if session.get("client_path"):
            client = session["client_path"]
            print(client)
            wildcard = glob.glob(client + "_*")
            print(wildcard)
            for directory in wildcard:
                try:
                    shutil.rmtree(directory)
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
        endpoint = f"v2/custom_templates?page={count}"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Api-Key": session["key"],
        }
        response = requests.get(url + endpoint, headers=headers)
        data = response.json()
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

        if data["data"] == []:
            break

    save_templates_backup(templates)
    return render_template(
        "templates.html",
        title="Templates",
        templates=templates,
    )


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
            + session["raw_school"]
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
    session["client_path"] = os.path.join(TEMPLATES_FOLDER, session["sani_school"])
    today = datetime.now(timezone.utc)
    today = today.strftime("%m-%d-%Y %H:%M:%S")
    session["client_path"] = session["client_path"] + "_" + str(today)
    if os.path.exists(session["client_path"]):
        pass
    else:
        os.mkdir(session["client_path"])

    for tupe in templates:
        file_name = tupe[0] + ".liquid"
        file_body = tupe[1]
        complete_path = os.path.join(session["client_path"], file_name)

        with open(complete_path, "w+") as temp:
            temp.write(file_body)
            temp.close


@app.route("/download_templates", methods=["GET", "POST"])
@key_required
def download_templates():
    zipped_file = f"{session['sani_school']}"
    zipped_file = zipped_file.replace(" ", "")
    zipped_file = zipped_file.replace("'", "")
    os.chdir = session["client_path"]
    file_path = session["client_path"]
    zipped_path = os.path.join(TEMPLATES_FOLDER, zipped_file)
    download = shutil.make_archive(zipped_path, "zip", file_path)
    delete_zip()
    return send_file(download, as_attachment=True)


def delete_zip():
    print("Sleeping...")
    time.sleep(5)
    zipped_path = TEMPLATES_FOLDER
    wildcard = glob.glob(zipped_path + "*.zip")
    wildcard = str(wildcard)
    wildzip = wildcard[-5:-2]
    if wildzip == "zip":
        try:
            path = Path(wildcard)
            print(path)
            shutil.rmtree(path)
        except OSError:
            print(OSError)
    return


@app.route("/get_info", methods=["GET", "POST"])
@key_required
def get_info():
    return render_template("get_info.html", title="Get Customer Information")


@app.route("/get_courses", methods=["GET", "POST"])
@key_required
def get_courses():
    print("course function running")
    count = 0
    courses = []
    cats = []
    course_dict = {}
    if request.method == "POST":
        while True:
            count += 1
            url = f"https://api.northpass.com/v2/courses?page={count}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url, headers=headers)
            data = response.json()

            for response in data["data"]:
                status = response["attributes"]["status"]
                uuid = response["id"]
                name = response["attributes"]["name"]
                ecount = response["attributes"]["enrollments_count"]
                created = response["attributes"]["created_at"]
                update = response["attributes"]["updated_at"]
                unpub = response["attributes"]["unpublished_changes"]
                course_dict = {
                    "Id": uuid,
                    "Name": name,
                    "Status": status,
                    "Enrollments": ecount,
                    "Created At": created,
                    "Last Updated": update,
                    "Unpublished Changes?": unpub,
                }
                cat_id = response["relationships"]["categories"]["data"]
                headers = {"accept": "application/json", "X-Api-Key": session["key"]}
                cats = []
                if len(cat_id) == 0:
                    pass
                elif len(cat_id) == 1:
                    categoryid = cat_id[0]["id"]
                    url = f"https://api.northpass.com/v2/categories/{categoryid}"
                    cat_resp = requests.get(url, headers=headers)
                    cat_data = cat_resp.json()
                    cat_name = cat_data["data"]["attributes"]["name"]
                    cats.append(cat_name)
                    course_dict.update({"Categories": cats})
                else:
                    for item in cat_id:
                        categoryid = item["id"]
                        url = f"https://api.northpass.com/v2/categories/{categoryid}"
                        cat_resp = requests.get(url, headers=headers)
                        cat_data = cat_resp.json()
                        cat_name = cat_data["data"]["attributes"]["name"]
                        cats.append(cat_name)
                        course_dict.update({"Categories": cats})

                try:
                    courses.append(course_dict)
                except TypeError as e:
                    print(f"Error: {e}")
                finally:
                    pd.set_option("display.max_colwidth", 30)
                    df = pd.DataFrame.from_records(courses)
                    # df.iloc[-1] = df.iloc[-1].astype(str).str.replace("[\]\[]",'')
                    df.fillna('', inplace=True)
                    courses_table = df.to_html()
                    session["dfcsv"] = df.to_csv()

            if data["data"] == []:
                break

        return render_template("get_info.html",
                              title="Course Information",
                              table=courses_table)

    return "You didn't post up"

@app.route("/get_groups", methods=["GET", "POST"])
@key_required
def get_groups():
    print("groups function running")
    count = 0
    groups = []
    group_dict = {}
    if request.method == "POST":
        while True:
            count += 1
            url = f"https://api.northpass.com/v2/groups?page={count}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url, headers=headers)
            data = response.json()
            print(data)

            for response in data["data"]:
                uuid = response["id"]
                name = response["attributes"]["name"]
                ecount = response["attributes"]["membership_count"]
                created = response["attributes"]["created_at"]
                update = response["attributes"]["updated_at"]
                elink = response["attributes"]["group_enrollment_link"]
                group_dict = {
                    "Id": uuid,
                    "Name": name,
                    "Members": ecount,
                    "Created At": created,
                    "Last Updated": update,
                    "Enrollment Link":elink,
                }
                try:
                    groups.append(group_dict)
                except TypeError as e:
                    print(f"Error: {e}")
                finally:
                    pd.set_option("display.max_colwidth", 30)
                    df = pd.DataFrame.from_records(groups)
                   #  df.iloc[-1] = df.iloc[-1].astype(str).str.replace("[\]\[]",'')
                    df.fillna('', inplace=True)
                    groups_table = df.to_html()
                    session["dfcsv"] = df.to_csv()
            if data["data"] == []:
                break
        return render_template("get_info.html",
                              title="Course Information",
                              table=groups_table)
    return "You didn't post up"


@app.route("/get_people", methods=["GET", "POST"])
@key_required
def get_people():
    print("groups function running")
    count = 0
    groups = []
    group_dict = {}
    if request.method == "POST":
        while True:
            count += 1
            url = f"https://api.northpass.com/v2/groups?page={count}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url, headers=headers)
            data = response.json()
            print(data)
@app.route("/undo_template", methods=["POST"])
@key_required
def undo_template():
    if request.method == "POST":
        if request.form["undo_templates"]:
            pass


@app.route("/stop", methods=["POST"])
def stop():
    print("stopping")
