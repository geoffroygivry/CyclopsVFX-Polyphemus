from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField


class shotForm(FlaskForm):
    username = StringField('fufu')
    password = PasswordField('password')