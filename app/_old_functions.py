
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
