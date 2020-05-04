from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo

class SignupForm(FlaskForm):
    username = StringField('Username', 
                validators=[DataRequired(), 
                Length(min=2, max=20)])
    email = StringField('Email',
            validators=[DataRequired(),
            Email()])
    password = PasswordField('Password',
                validators=[DataRequired(),
                Length(8)])
    confirm_password = PasswordField('Confirm Password',
                        validators=[DataRequired(),
                        EqualTo('password'),
                        Length(8)])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email',
            validators=[DataRequired(),
            Email()])
    password = PasswordField('Password',
                validators=[DataRequired(),
                Length(8)])
    remember = BooleanField('Remember me')
    submit = SubmitField('Login')