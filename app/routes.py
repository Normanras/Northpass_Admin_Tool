from app import app
from flask import request, Flask, flash, render_template, session, make_response
import requests
import json
import itertools
import pandas as pd
import re


@app.route("/", methods=["GET", "POST"])
def ask_key():
    session.clear()
    if request.method == "POST":
        session["key"] = request.form.get("apikey")
        if re.search("\s", session["key"]):
            error = "Hm. That doesn't seem right"
            return render_template("index.html", title="Home", error=error)
        elif session["key"] is not None and len(session["key"]) > 10:
            url = "https://api.northpass.com/v2/properties/school"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url, headers=headers)
            data = response.json()
            session["school"] = data["data"]["attributes"]["properties"]["name"]
            print(session["school"])
            return render_template("options.html", title="Options")
        else:
            error = "Hm. That doesn't seem right"
            return render_template("index.html", title="Home", error=error)

    else:
        return render_template("index.html", title="Home")


@app.route("/", methods=["GET", "POST"])
def render_home():
    return render_template("index.html", title="Home")


@app.route("/get_courses", methods=["GET", "POST"])
def get_courses():
    array = []
    course_dict = {}
    df = pd.DataFrame()
    tempdf = pd.DataFrame()
    pd.set_option("display.max_colwidth", 100)
    x = 0

    if request.method == "POST":
        while True:
            x += 1
            url = f"https://api.northpass.com/v2/courses?page={x}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url, headers=headers)
            jsonresponse = response.json()
            data = response.json()
            nextlink = data["links"]

            for response in data["data"]:
                uuid = response["id"]
                course_dict = {"id": uuid}
                for keys, values in response["attributes"].items():
                    course_dict[keys] = values
                array.append(course_dict)
                dataframe = pd.DataFrame(array).drop("list_image_url", axis=1)
            print(dataframe)

            if "next" not in nextlink:
                break

        dfcourse = dataframe.to_html()
        session["dfcsv"] = dataframe.to_csv()
        return render_template("table.html", table=dfcourse, title="List of Courses")
    else:
        return "This isn't working. Let's go our own way."


@app.route("/table")
def table():
    return render_template("table.html", tables=[session["dfhtml"]], titles=["Table"])


@app.route("/downloadcsv", methods=["GET", "POST"])
def download_csv():
    if request.method == "GET":
        download = make_response(session["dfcsv"])
        download.headers["Content-Disposition"] = "attachment; filename=export.csv"
        download.headers["Content-Type"] = "text/csv"
        return download


@app.route("/get_people", methods=["GET", "POST"])
def get_people():
    array = []
    ppl_dict = {}
    df = pd.DataFrame()
    x = 0

    if request.method == "POST":
        while True:
            x += 1
            url = f"https://api.northpass.com/v2/people?page={x}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url, headers=headers)
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
        return render_template("table.html", table=dfppl, title="List of People")
    else:
        return "what what"


@app.route("/add_ppl_options", methods=["POST"])
def add_ppl_options():
    array = []
    dict_response = {}
    df = pd.DataFrame()
    x = 0
    if request.method == "POST":
        while True:
            x += 1
            url = f"https://api.northpass.com/v2/groups?page={x}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url, headers=headers)
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

        dfgroups = dataframe.to_html()
        session["dfcsv"] = dataframe.to_csv()
        return render_template(
            "bulk_add_ppl.html", table=dfgroups, titles="Bulk Add Learners"
        )
    else:
        return "This isn't working. Let's go our own way."


@app.route("/bulk_add_ppl", methods=["GET", "POST"])
def bulk_add_ppl():
    emailarr = []
    grouparr = []
    if request.method == "POST":
        emails = request.form.get("emails")
        groups = request.form.get("groups")
        emails = emails.split(",")
        groups = groups.split(",")
        url = "https://api.northpass.com/v2/bulk/people"
        combinations = list(itertools.product(emails, groups))
        print(combinations)
        payload = {
            "data": {"attributes": {"people": [{"email": emails, "groups": groups}]}}
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Api-Key": session["key"],
        }
    return payload


@app.route("/add_groups_options", methods=["POST"])
def add_groups_options():
    array = []
    dict_response = {}
    df = pd.DataFrame()
    x = 0
    if request.method == "POST":
        while True:
            x += 1
            url = f"https://api.northpass.com/v2/groups?page={x}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url, headers=headers)
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


@app.route("/bulk_add_groups", methods=["GET", "POST"])
def bulk_add_groups():
    grouparr = []
    i = 0
    if request.method == "POST":
        groups = request.form.get("groups")
        if "\n" in groups:
            groups = groups.split("\n")
            groups = [group.strip() for group in groups]
        elif "," in groups:
            groups = groups.split(",")
            groups = [group.strip() for group in groups]
        for group in groups:
            groupdict = {}
            groupdict["name"] = group
            grouparr.append(groupdict)

        url = "https://api.northpass.com/v2/bulk/groups"
        payload = {"data": {"attributes": {"groups": grouparr}}}
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Api-Key": session["key"],
        }
        response = requests.post(url, json=payload, headers=headers)
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
            error = "Uh oh. Looks like you're not the admin or don't have appropriate privileges. Please talk to your academy admin."
        elif "422" in response:
            error = "Hm. Looks like something was wrong with the group names. Reach out to the manager of this app."
            return render_template(
                "bulk_add_groups.html",
                table=session["dfgroups"],
                title="Groups Added",
                error=error,
            )
        else:
            error = "Shrug"
            return render_template("bulk_add_groups.html", title="Shrug", error=error)


app.secret_key = "@&I\x1a?\xce\x94\xbb0w\x17\xbf&Y\xa2\xc2(A\xf5\xf2\x97\xba\xeb\xfa"


if __name__ == "__main__":
    ask_key()
