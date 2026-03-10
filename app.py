from flask import Flask
from config import Config
from extensions import db, login_manager
from models import User
from routes.events_api import events_api
from routes.views import views
from routes.auth import auth

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(events_api)
    app.register_blueprint(views)
    app.register_blueprint(auth)

    with app.app_context():
        db.create_all()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)