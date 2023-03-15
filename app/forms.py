from flask_wtf import FlaskForm
from wtforms.fields import (SubmitField,
                            PasswordField,
                            StringField,
                            TextAreaField,
                            IntegerField,
                            BooleanField,
                            RadioField)
from wtforms.validators import InputRequired, Length
from flask_wtf.file import FileField, FileRequired
from werkzeug.utils import secure_filename
from flask_codemirror.fields import CodeMirrorField


class ApiKey(FlaskForm):
    api_key = PasswordField('Api Key',
                            validators=[InputRequired(),
                                        Length(min=20, max=25)]
                            )


class TemplateForm(FlaskForm):
    name = StringField("Template File Name",
                       validators=[InputRequired()])

    body = TextAreaField("Template Code",
                         validators=[InputRequired()])

    submit = SubmitField('Upload Templates')

    # template_code = CodeMirrorField( language='htmlembedded',
           # config={'lineNumbers': 'true'})

class CsvForm(FlaskForm):
    file = FileField(validators=[FileRequired()])
    all_or_some = RadioField("All or Some",
                             choices=['All learners in all groups',
                                      'Learners only in adjacent groups'],
                             validators=[InputRequired()])



class CourseForm(FlaskForm):
    title = StringField('Title',
                        validators=[InputRequired(),
                            Length(min=10, max=100)])
    description = TextAreaField('Course Description',
                                validators=[InputRequired(),
                                            Length(max=200)])
    price = IntegerField('Price', validators=[InputRequired()])
    level = RadioField('Level',
                       choices=['Beginner', 'Intermediate', 'Advanced'],
                       validators=[InputRequired()])
    available = BooleanField('Available', default='checked')

