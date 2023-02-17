from app import app
from flask import request, Flask, flash, render_template, session, make_response
import requests
import json
import pandas as pd
import re


@app.route("/", methods=["GET", "POST"])
def ask_key():
    if request.method == "POST":
        session['key'] = request.form.get('apikey')
        print(session['key'])
        flash(session['key'])
        if re.search(r'(\S+\w+)', session['key']) and len(session['key']) > 5:
            print("regex worked")
            print(len(session['key']))
            return render_template("get.html", title="Options")
        else:
            error = "Hm. That doesn't seem right"
            return render_template("index.html", title="Home", error=error)
    else:
        return render_template("index.html", title="Home")


@app.route("/get_courses", methods=["GET", "POST"])
def get_courses():
    array = []
    df = pd.DataFrame()
    if request.method == "POST":
        url = "https://api.northpass.com/v2/courses"
        headers = {"accept": "application/json", "X-Api-Key": session['key']}
        response = requests.get(url, headers=headers)
        jsonresponse = response.json()
        dt = jsonresponse["data"]
        for course in dt:
            df = df.append(course["attributes"], ignore_index=True)
    else:
        return "This isn't working. Let's go our own way."
    print(df)
    download = make_response(df.to_csv())
    download.headers["Content-Disposition"] = "attachment; filename=export.csv"
    download.headers["Content-Type"] = "text/csv"
    return download


@app.route("/get_people", methods=["GET", "POST"])
def get_people():
    print(session['key'])
    if request.method == "POST":
        url = "https://api.northpass.com/v2/people"
        headers = {"accept": "application/json", "X-Api-Key": session['key']}
        response = requests.get(url, headers=headers)
        jsonresponse = response.json()
        dt = jsonresponse
        person = dt
        print(person)
        return person
    else:
        return "what what"


@app.route("/startpage", methods=["GET", "POST"])
def startpage():
    return render_template("startpage.html", title="StartTest")


app.secret_key = "@&I\x1a?\xce\x94\xbb0w\x17\xbf&Y\xa2\xc2(A\xf5\xf2\x97\xba\xeb\xfa"


if __name__ == "__main__":
    ask_key()
