from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired


class RequestForm(FlaskForm):
    apikey = StringField("Academy API Key", validators=[DataRequired()])
    submit = SubmitField("Submit")
