from dotenv import load_dotenv
load_dotenv()
import os

from datetime import timedelta

class ApplicationConfig:

    JWT_SECRET_KEY=os.environ["JWT_SECRET_KEY"]
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=24)
    JWT_COOKIE_SECURE=True


    SECRET_KEY=os.environ["SECRET_KEY"]


    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = os.environ["SQLALCHEMY_DATABASE_URI"]

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ["MAIL_USERNAME"]
    MAIL_PASSWORD = os.environ["MAIL_PASSWORD"]