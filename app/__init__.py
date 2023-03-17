from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Upload folder
#UPLOAD_FOLDER = "/Users/normrasmussen/Documents/Projects/CSM_webapp/app/static/files"
# UPLOAD_FOLDER = 'static/files'
#app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
#ALLOWED_EXTENSIONS = {"csv"}

from app import routes
