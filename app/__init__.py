from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Upload folder
UPLOAD_FOLDER = 'static/files'
app.config['UPLOAD_FOLDER'] =UPLOAD_FOLDER

from app import routes
