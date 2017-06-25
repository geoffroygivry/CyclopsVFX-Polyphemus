from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField


class ShotForm(FlaskForm):
    asset_task = SelectField('Add Asset task:', id='asset-task')
    asset_users = SelectField('Add Assignee:', id='asset-task-user')
    submit = SubmitField('submit')
