from flask_wtf import FlaskForm
from wtforms.fields import SubmitField
from flask_codemirror.fields import CodeMirrorField

class TemplateForm(FlaskForm):
    template_code = CodeMirrorField(
            language='htmlembedded',
            config={'lineNumbers': 'true'})
    submit = SubmitField('Submit')

