import pytest
from unittest.mock import MagicMock, patch
from flask import Flask
from flask_login import LoginManager
from extensions import db
from models import User, Event
from routes.events_api import events_api
from datetime import datetime

# [datetime.datetime(2026, 4, 1, 0, 0), datetime.datetime(2026, 4, 2, 0, 0), datetime.datetime(2026, 4, 3, 0, 0)]

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "testkey",
    })
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(events_api)

    with app.app_context():
        db.create_all()
        user = User(username="testuser", password="123")
        db.session.add(user)
        db.session.commit()

    yield app

    with app.app_context():
        db.drop_all()

@pytest.fixture
def client(app):
    client = app.test_client()

    with app.app_context():
        user = User.query.first()

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)

    return client, user

@pytest.fixture
def mock_event(app):
    with app.app_context():
        event = MagicMock()
        event.id = 1
        event.title = "Test Event"
        event.start = "2026-04-01"
        event.end = "2026-04-01"
        event.time = "10:00"
        event.desc = "Description"
        event.color = "#ff0000"
        event.is_all_day = False
        event.recurrence = "FREQ=DAILY;COUNT=3"

    return event

def test_rrule_expand_success(app, client, mock_event):
    client, test_user = client

    # 模擬 RRULE 展開結果
    mock_instances = [
        datetime(2026, 4, 1),
        datetime(2026, 4, 2),
        datetime(2026, 4, 3)
    ]

    mock_rrule = MagicMock()
    mock_rrule.between.return_value = mock_instances

    with app.app_context():
        with patch("dateutil.rrule.rrulestr", return_value=mock_rrule):
            with patch("models.Event.query") as mock_query:
                mock_event.recurrence = "FREQ=DAILY;COUNT=3"
                mock_query.filter_by.return_value.all.return_value = [mock_event]
                response = client.get("/api/events/")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == len(mock_instances)
    assert data[0]["start"] == "2026-04-01"