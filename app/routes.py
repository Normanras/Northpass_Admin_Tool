from app import app
from flask import request, Flask, flash, render_template, session, make_response
import requests
import json
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
            dt = jsonresponse["data"]
            next = jsonresponse["links"]

            for course in dt:
                df = df.append(course["attributes"], ignore_index=True)
            # df = df.drop("list_image_url", axis=1)

            if "next" not in next:
                break

        dfhtml = df.to_html(col_space=5)
        session["dfcsv"] = df.to_csv()
        return render_template("table.html", tables=dfhtml, titles="Course List")

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
    df = pd.DataFrame()
    x = 0

    if request.method == "POST":
        while True:
            x += 1
            url = f"https://api.northpass.com/v2/people?page={x}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url, headers=headers)
            jsonresponse = response.json()
            dt = jsonresponse["data"]
            next = jsonresponse["links"]

            for person in dt:
                print(person)
                df = df.append(person["attributes"], ignore_index=True)

            if "next" not in next:
                break

        dfppl = df.to_html(col_space=5)
        session["dfcsv"] = df.to_csv()
        return render_template("table.html", tables=dfppl, titles="People List")

    else:
        return "what what"


@app.route("/add_options", methods=["POST"])
def add_options():
    array = []
    df = pd.DataFrame()
    x = 0
    if request.method == "POST":
        while True:
            x += 1
            url = f"https://api.northpass.com/v2/groups?page={x}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url, headers=headers)
            data = response.text
            df = pd.json_normalize(data)
            print(df)

            # print(type(response))
            # print(response)
            # jsonresponse = response.json()
            # dt = jsonresponse["data"]
            # next = jsonresponse["links"]

            for group in dt:
                df = df.from_dict(group["attributes"], orient="index")
                # df = df.append(group["id"], ignore_index=True)
                # df = df.append(group["attributes"], ignore_index=True)

            if "next" not in next:
                break

        print(df)
        session["dfcsv"] = df.to_csv()
        dfgroups = df.to_html(col_space=5)
        return render_template(
            "bulk_add.html", tables=dfgroups, titles="Bulk Add Learners"
        )


@app.route("/bulk_add", methods=["GET", "POST"])
def bulk_add():
    if request.method == "POST":
        emails = request.form.get("emails")
        groups = request.form.get("groups")
        url = "https://api.northpass.com/v2/bulk/people"

        payload = {
            "data": {"attributes": {"people": [{"email": emails, "groups": groups}]}}
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Api-Key": session["key"],
        }


app.secret_key = "@&I\x1a?\xce\x94\xbb0w\x17\xbf&Y\xa2\xc2(A\xf5\xf2\x97\xba\xeb\xfa"


if __name__ == "__main__":
    ask_key()
