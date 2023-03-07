import requests
import itertools
import pandas as pd
import re
import os
import glob
from app import app
from flask import (
    redirect,
    flash,
    request,
    render_template,
    session,
    make_response,
    url_for,
)
from werkzeug.utils import secure_filename

# Global Variables
url = "https://api.northpass.com/"

# Upload folder
UPLOAD_FOLDER = "/Users/normrasmussen/Documents/Projects/CSM_webapp/app/static/files"
# UPLOAD_FOLDER = 'static/files'
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"csv"}


def download_csv():
    if request.method == "GET":
        download = make_response(session["dfcsv"])
        download.headers["Content-Disposition"] = "attachment; filename=export.csv"
        download.headers["Content-Type"] = "text/csv"
        return download


def key_response(response):
    if "402" in str(response):
        error = response.text
        return render_template("index.html", title="Error Home", errors=error)
    if "401" in str(response):
        error = [
            "Unauthorized access error.",
            "This can mean a lot of things,",
            "such as the key being changed.",
            "Remember, they are paired to each educator!",
        ]
        return render_template("index.html", title="Error Home", errors=error)
    return correct_key(response)


def correct_key(response):
    data = response.json()
    session["school"] = data["data"]["attributes"]["properties"]["name"]
    print(session["school"])
    return render_template("options.html", title="Options")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/dev", methods=["GET", "POST"])
def dev_test():
    return render_template("options.html", title="Dev Test")


# DONE: Remove header for main page.
# TODO: Leave boxes but change outcome depending if file has been uploaded.
"""
So create a session['file'] variable with the recently uploaded file name.
Then, when someone clicks one of the buttons,
after that if request == "POST",
create a secondary if statement for if file == session['file'],
directly upload emails etc else,
bring to the secondary pages already created and
allow them to copy and paste.
"""


@app.route("/", methods=["GET", "POST"])
def ask_key():
    """This is the main function that asks for the API Key.
    Without this key, no other functions will work.
    It also assigns the api key to the session and clears the session upon each reload.
    """
    if session.get("key"):
        return render_template("options.html", title="Options Home")
    if request.method == "POST":
        session["key"] = request.form.get("apikey")
        # if re.search(r"\s", session["key"]):
        #    error = "Hm. That doesn't seem right"
        #    return render_template("index.html", title="Home", errors=error)
        if session["key"] is not None and len(session["key"]) > 10:
            endpoint = "/v2/properties/school"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url + endpoint, headers=headers)
            return key_response(response)
        error = "Hm. That doesn't seem right"
        return render_template("index.html", title="Home", error=error)

    return render_template("index.html", title="Home")


@app.route("/", methods=["GET", "POST"])
def render_home():
    if session.get("key"):
        return render_template("options.html", title="Home")
    return render_template("index.html", title="Enter Key")


@app.route("/options", methods=["GET", "POST"])
@app.route("/", methods=["GET", "POST"])
def clear_session():
    session.clear()
    return render_template("index.html", title="Home, New session")


"""
uploaded_file = request.files['file']
if  uploaded_file.filename != '':
print("File has name")
uploaded_file.save(uploaded_file.filename)
return render_template("options.html", title="Home, Now with CSV!")
"""


@app.route("/csv", methods=["GET", "POST"])
def csv():
    print("Uploading CSV")
    csvData = pd.DataFrame()
    if request.method == "POST":
        if "file" not in request.files:
            print("file not in request.files")
            flash("No file found or uploaded")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            print("no file exists")
            flash("No file found or uploaded")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            session["file"] = filename
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            session["filepath"] = file_path
            file.save(file_path)
            csvData = pd.read_csv(file_path, usecols=["Email"], index_col=False)
            html_data = csvData.to_html()
            return render_template(
                "options.html", table=html_data, title="Uploaded File"
            )
        # TODO: Figure out how to delete the file after use.
    print("nothing happened")
    return render_template("options.html", title="Home, now with a CSV Table!")


@app.route("/table")
def table():
    return render_template("table.html", tables=[session["dfhtml"]], titles=["Table"])


@app.route("/get_courses", methods=["GET", "POST"])
def get_courses():
    array = []
    course_dict = {}
    pd.set_option("display.max_colwidth", 100)
    count = 0
    dataframe = pd.DataFrame()

    if request.method == "POST":
        while True:
            count += 1
            endpoint = f"v2/courses?page={count}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url + endpoint, headers=headers)
            data = response.json()
            nextlink = data["links"]

            for response in data["data"]:
                uuid = response["id"]
                course_dict = {"id": uuid}
                for keys, values in response["attributes"].items():
                    course_dict[keys] = values
                array.append(course_dict)
                dataframe = pd.DataFrame(array).drop(
                    ["list_image_url", "permalink"], axis=1
                )
                dataframe["full_description"] = dataframe[
                    "full_description"
                ].str.replace(r"<[^<>]*>", "", regex=True)
                print(dataframe)

            if "next" not in nextlink:
                break

        dfcourse = dataframe.to_html()
        session["dfcsv"] = dataframe.to_csv()
        return render_template("get.html", table=dfcourse, title="List of Courses")
    else:
        return "This isn't working. Let's go our own way."


@app.route("/get_people", methods=["GET", "POST"])
def get_people():
    array = []
    ppl_dict = {}
    count = 0
    dataframe = pd.DataFrame()

    if request.method == "POST":
        print("get People POST")
        while True:
            count += 1
            endpoint = f"v2/people?page={count}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url + endpoint, headers=headers)
            data = response.json()
            nextlink = data["links"]

            for response in data["data"]:
                uuid = response["id"]
                ppl_dict = {"id": uuid}
                for keys, values in response["attributes"].items():
                    ppl_dict[keys] = values
                array.append(ppl_dict)
                dataframe = pd.DataFrame(array).drop("custom_avatar_url", axis=1)
                print(dataframe)

            if "next" not in nextlink:
                break

        dfppl = dataframe.to_html()
        session["dfcsv"] = dataframe.to_csv()
        return render_template("get.html", table=dfppl, title="List of People")
    else:
        return render_template("get.html", error="Something went wrong")


@app.route("/bulk_add_opts", methods=["GET", "POST"])
def bulk_add_opts():
    array = []
    dict_response = {}
    dataframe = pd.DataFrame()
    count = 0

    if request.method == "POST":
        if session.get("file"):
            print("file exists! uploading data...")
            return "File Exists! Test Complete"
        else:
            while True:
                count += 1
                endpoint = f"v2/groups?page={count}"
                headers = {"accept": "application/json", "X-Api-Key": session["key"]}
                response = requests.get(url + endpoint, headers=headers)
                data = response.json()
                nextlink = data["links"]

                for response in data["data"]:
                    uuid = response["id"]
                    dict_response = {"id": uuid}
                    for keys, values in response["attributes"].items():
                        dict_response[keys] = values
                    array.append(dict_response)
                    dataframe = pd.DataFrame(array).drop(
                        "group_enrollment_link", axis=1
                    )
                print(dataframe)

                if "next" not in nextlink:
                    break

            dfgroups = dataframe.to_html()
            session["dfcsv"] = dataframe.to_csv()
            return render_template(
                "bulk_add.html", table=dfgroups, titles="Bulk Add"
            )
    else:
        return "This isn't working. Let's go our own way."


@app.route("/bulk_add_groups_opts", methods=["GET", "POST"])
def bulk_add_groups_opts():
    array = []
    dict_response = {}
    count = 0
    dataframe = pd.DataFrame()

    if request.method == "POST":
        while True:
            count += 1
            endpoint = f"v2/groups?page={count}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url + endpoint, headers=headers)
            data = response.json()
            nextlink = data["links"]

            for response in data["data"]:
                uuid = response["id"]
                dict_response = {"id": uuid}
                for keys, values in response["attributes"].items():
                    dict_response[keys] = values
                array.append(dict_response)
                dataframe = pd.DataFrame(array).drop("group_enrollment_link", axis=1)
            print(dataframe)

            if "next" not in nextlink:
                break

        session["dfgroups"] = dataframe.to_html()
        session["dfcsv"] = dataframe.to_csv()
        return render_template(
            "bulk_add_groups.html", table=session["dfgroups"], titles="Bulk Add Groups"
        )
    else:
        return "This isn't working. Let's go our own way."


@app.route("/options", methods=["GET", "POST"])
def ppl_to_groups_opts():
    pass


@app.route("/bulk_add", methods=["GET", "POST"])
def bulk_add():
    if request.method == "POST":
        emails = request.form.get("emails")
        groups = request.form.get("groups")
        print(emails)
        print(type(emails))
        if emails:
            if "\n" in emails:
                emails = emails.split("\n")
                emails = [email.strip() for email in emails]
                print(emails)
                print(type(emails))
                # return api_add_ppl_groups(emails, groups)
            elif "," in emails:
                emails = emails.split(",")
                emails = [email.strip() for email in emails]
                # return api_add_ppl_groups(emails, groups)
        if groups:
            if "\n" in groups:
                groups.split("\n")
                groups = [group.strip() for group in groups]
            elif "," in groups:
                groups.split(",")
                groups = [group.strip() for group in groups]

#        print(groups)
#        print(type(groups))
#        print(emails)
#        print(type(emails))

    return render_template('bulk_add.html')


#    for group in groups:
#    groupdict = {}
    groupdict["name"] = group

def api_add_ppl(emails):
    pass


def api_add_groups(groups):
    pass


def api_add_ppl_groups(emails, groups):
    if not emails:
        if not groups:
            endpoint = "v2/bulk/people"
            combinations = list(itertools.product(emails, groups))
            print(combinations)
            payload = {
                "data": {
                    "attributes": {"people": [{"email": emails, "groups": groups}]}
                }
            }
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "X-Api-Key": session["key"],
            }
            response = requests.post(url + endpoint, json=payload, headers=headers)
            response = str(response)
            if "202" in response:
                error = "Success! People have been added successfully."
                return render_template(
                    "bulk_add_ppl.html",
                    table=session["dfgroups"],
                    title="People Added",
                    error=error,
                )
            elif "403" in response:
                error = "Uh oh. Looks like you don't have appropriate privileges."
            elif "422" in response:
                error = "Hm. Looks like something was wrong with the names."
                return render_template(
                    "bulk_add_people.html",
                    table=session["dfgroups"],
                    title="People Added",
                    error=error,
                )
            else:
                error = "Shrug"
                return render_template("bulk_add_ppl.html", title="Shrug", errors=error)
        endpoint = "v2/bulk/people"
        payload = {"data": {"attributes": {"people": [{"email": emails}]}}}
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Api-Key": session["key"],
        }
        response = requests.post(url + endpoint, json=payload, headers=headers)
        response = str(response)
        if "202" in response:
            error = "Success! People have been added successfully."
            return render_template(
                "bulk_add_ppl.html",
                table=session["dfgroups"],
                title="People Added",
                error=error,
            )
        elif "403" in response:
            error = "Uh oh. Looks like you don't have appropriate privileges."
        elif "422" in response:
            error = "Hm. Looks like something was wrong with the names."
            return render_template(
                "bulk_add_people.html",
                table=session["dfgroups"],
                title="People Added",
                error=error,
            )
        else:
            error = "Shrug"
            return render_template("bulk_add_ppl.html", title="Shrug", errors=error)
    error = "No Data was Loaded. Try again, bozo."
    return render_template("bulk_add_ppl.html", title="No Data", errors=error)


@app.route("/templates", methods=["GET", "POST"])
def templates():
    pass


@app.route("/bulk_add_groups", methods=["GET", "POST"])
def bulk_add_groups():
    grouparr = []
    count = 0
    if request.method == "POST":
        groups = request.form.get("groups")
        if "\n" in groups:
            groups.split("\n")
            groups = [group.strip() for group in groups]
        elif "," in groups:
            groups.split(",")
            groups = [group.strip() for group in groups]
        for group in groups:
            groupdict = {}
            groupdict["name"] = group
            grouparr.append(groupdict)

        endpoint = "v2/bulk/groups"
        payload = {"data": {"attributes": {"groups": grouparr}}}
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Api-Key": session["key"],
        }
        response = requests.post(url + endpoint, json=payload, headers=headers)
        print(type(response))
        response = str(response)
        if "202" in response:
            error = "Success! Groups have been added successfully."
            return render_template(
                "bulk_add_groups.html",
                table=session["dfgroups"],
                title="Groups Added",
                error=error,
            )
        elif "403" in response:
            error = [
                "Uh oh. Looks like you're not the",
                "admin or don't have appropriate privileges.",
                "Please talk to your academy admin.",
            ]
        elif "422" in response:
            error = [
                "Hm. Looks like something was wrong with the group names.",
                "Reach out to the manager of this app.",
            ]
            return render_template(
                "bulk_add_groups.html",
                table=session["dfgroups"],
                title="Groups Added",
                error=error,
            )
        else:
            error = "Shrug"
            return render_template("bulk_add_groups.html", title="Shrug", errors=error)


@app.route("/bulk_courses_to_groups", methods=["GET", "POST"])
def bulk_courses_to_groups():
    pass


@app.route("/bulk_invite_ppl", methods=["GET", "POST"])
def bulk_invite_ppl():
    pass


# @app.teardown_request
# def clear_session():
#    session.clear()

app.secret_key = "@&I\x1a?\xce\x94\xbb0w\x17\xbf&Y\xa2\xc2(A\xf5\xf2\x97\xba\xeb\xfa"


if __name__ == "__main__":
    ask_key()
