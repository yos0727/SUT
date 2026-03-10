from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()

# 新增 LoginManager
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # 若未登入，導向此路由