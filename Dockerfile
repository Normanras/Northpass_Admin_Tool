FROM python:3.11
COPY ./requirements.txt /
WORKDIR /
RUN pip install -r requirements.txt
COPY . /
EXPOSE 5005
CMD [ "flask", "run", "--host=0.0.0.0"]
