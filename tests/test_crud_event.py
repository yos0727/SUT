import pytest
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify
from flask_login import LoginManager, login_user, UserMixin
from extensions import db
from models import User, Event
from routes.events_api import events_api

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
def mock_db_session():
    with patch("extensions.db.session") as mock_db:
        yield mock_db

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
        event = MagicMock(spec=Event)
        event.id = 1
        event.title = "Old Title"
        event.start = "2026-03-31"
        event.end = "2026-03-31"
        event.time = "12:00"
        event.desc = "Old description"
        event.color = "#ffcccc"
        event.is_all_day = False
        event.recurrence = ""

    return event

def test_create_event_fail(client, mock_db_session):
    client, test_user = client

    data = {
        "title": "Test Event",
        "start": "2026-03-31",
        "end": "2026-03-31",
        "is_all_day": True
    }

    mock_db_session.commit.side_effect = Exception("DB Error")

    response = client.post("/api/events/", json=data)

    assert response.status_code == 500
    assert b"Internal Server Error" in response.data

def test_update_event_success(app, client, mock_db_session, mock_event):
    client, test_user = client

    data = {
        "title": "New Event",
        "is_all_day": True
    }

    with app.app_context():
        with patch("models.Event.query") as mock_query:
            mock_query.filter_by.return_value.first_or_404.return_value = mock_event

            response = client.put(f"/api/events/{mock_event.id}", json=data)

    assert response.status_code == 200
    assert mock_event.title == "New Event"
    assert mock_event.is_all_day is True
    assert mock_event.time == ""

    mock_db_session.commit.assert_called_once()