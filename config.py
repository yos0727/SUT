import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'events.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 新增：用於加密 session 和 cookie
    SECRET_KEY = 'your-super-secret-key'