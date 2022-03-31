from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, InputRequired

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Senha',[InputRequired(), EqualTo('confirm_password', message='As senhas precisam ser iguais'), Length(min=8, message="A senha precisa ter no mínimo 8 dígitos")])
    confirm_password = PasswordField('Confirme a Senha ')
    submit = SubmitField(label='Alterar Senha (8 dígitos no mínimo)')
