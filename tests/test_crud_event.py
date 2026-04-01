import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify
from flask_login import LoginManager, login_user, UserMixin
from werkzeug.exceptions import NotFound

from extensions import db
from models import User, Event
from routes.events_api import events_api
from app import create_app
from utils import serialize_event


@pytest.fixture
def client_a():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['LOGIN_DISABLED'] = True 
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_current_user():
    with mock.patch("routes.events_api.current_user") as m:
        m.id = 1
        yield m

@pytest.fixture
def mock_event_model():
    with mock.patch("routes.events_api.Event") as m:
        yield m

@pytest.fixture
def mock_db():
    with mock.patch("routes.events_api.db.session") as m:
        yield m


@pytest.fixture
def app_b():
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
def client_b(app_b):
    client = app_b.test_client()

    with app_b.app_context():
        user = User.query.first()

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)

    return client, user

@pytest.fixture
def mock_event(app_b):
    with app_b.app_context():
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


def test_get_events_success(client_a, mock_current_user, mock_event_model):
    fake_event_1_dict = {
        "id": 101,
        "title": "SEP deadline",
        "start": "2026-04-10",
        "end": "2026-04-10",
        "time": "14:00",
        "desc": "討論專案",
        "color": "#ffcccc",
        "is_all_day": False,
        "recurrence": ""
    }
    
    fake_event_2_dict = {
        "id": 102,
        "title": "吃飯",
        "start": "2026-04-15",
        "end": "2026-04-15",
        "time": "18:30",
        "desc": "部門吃飯",
        "color": "#ccccff",
        "is_all_day": False,
        "recurrence": ""
    }

    mock_event_model.query.filter_by.return_value.all.return_value = [
        mock.Mock(**fake_event_1_dict),
        mock.Mock(**fake_event_2_dict)
    ]

    response = client_a.get('/api/events/')
    data = response.get_json()

    assert response.status_code == 200
    mock_event_model.query.filter_by.assert_called_once_with(user_id=mock_current_user.id)
    
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["id"] == 101
    assert data[0]["title"] == "SEP deadline"
    assert data[1]["id"] == 102
    assert data[1]["title"] == "吃飯"

def test_get_events_unauth(client_a, mock_event_model):
    client_a.application.config['LOGIN_DISABLED'] = False
    response = client_a.get("/api/events/")
    assert response.status_code == 302 or response.status_code == 401
    mock_event_model.query.filter_by.assert_not_called()

def test_create_event_success(client_a, mock_current_user, mock_db):
    new_data_dict = {
        "id": 101,
        "title": "SEP deadline",
        "start": "2026-04-10",
        "end": "2026-04-10",
        "time": "14:00",
        "desc": "討論專案",
        "color": "#ffcccc",
        "is_all_day": False,
        "recurrence": "",
        'user_id' : mock_current_user.id,   
    }
    response = client_a.post("/api/events/", json=new_data_dict)
    assert response.status_code == 201
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

    created_event = mock_db.add.call_args[0][0]

    assert created_event.title == "SEP deadline"
    assert created_event.start == "2026-04-10"
    assert created_event.end == "2026-04-10"
    assert created_event.time == "14:00"
    assert created_event.desc == "討論專案"
    assert created_event.color == "#ffcccc"
    assert created_event.is_all_day == False
    assert created_event.user_id == 1

def test_create_allday_event(client_a, mock_current_user, mock_db):
    new_data_dict = {
        "id": 102,
        "title": "全日活動",
        "start": "2026-04-01",
        "end": "2026-04-01",
        "is_all_day": True,
        'user_id' : mock_current_user.id,   
    }
    response = client_a.post("/api/events/", json=new_data_dict)
    assert response.status_code == 201
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

    created_event = mock_db.add.call_args[0][0]

    assert created_event.title == "全日活動"
    assert created_event.start == "2026-04-01"
    assert created_event.end == "2026-04-01"
    assert created_event.time == ""  
    assert created_event.desc == ""
    assert created_event.color == "#ffcccc"  
    assert created_event.is_all_day == True
    assert created_event.user_id == 1

def test_create_event_fail(client_b, mock_db_session):
    client, test_user = client_b

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

def test_update_event_success(app_b, client_b, mock_db_session, mock_event):
    client, test_user = client_b

    expect_result = {
        'id' : 1,
        'title' : "New Title",
        'start' : "2026-04-11",
        'end' : "2026-04-11",
        'time' : "",
        'desc' : "New description",
        'color' : "#ffffff",
        'is_all_day' : True,
        'recurrence' : "FREQ=WEEKLY"
    }

    with app_b.app_context():
        with patch("models.Event.query") as mock_query:
            mock_query.filter_by.return_value.first_or_404.return_value = mock_event
            response = client.put(f"/api/events/{mock_event.id}", json=expect_result)

    result = serialize_event(mock_event)

    assert response.status_code == 200
    assert result == expect_result
    mock_db_session.commit.assert_called_once()

def test_update_event_not_found(app_b, client_b, mock_db_session, mock_event):
    client, test_user = client_b

    data = {
        "title": "New Event",
        "is_all_day": True
    }

    with app_b.app_context():
        with patch("models.Event.query") as mock_query:
            mock_query.filter_by.return_value.first_or_404.side_effect = NotFound()

            response = client.put(f"/api/events/0", json=data)

    assert response.status_code == 404
    mock_db_session.commit.assert_not_called()

def test_update_partial_data(app_b, client_b, mock_db_session, mock_event):
    client, test_user = client_b

    partial_data = {
        "title": "New Title",
    }

    expect_result = {
        'id' : 1,
        'title' : "New Title",
        'start' : "2026-03-31",
        'end' : "2026-03-31",
        'time' : "12:00",
        'desc' : "Old description",
        'color' : "#ffcccc",
        'is_all_day' : False,
        'recurrence' : ""
    }

    with app_b.app_context():
        with patch("models.Event.query") as mock_query:
            mock_query.filter_by.return_value.first_or_404.return_value = mock_event
            response = client.put(f"/api/events/{mock_event.id}", json=partial_data)

    result = serialize_event(mock_event)

    assert response.status_code == 200
    assert result == expect_result
    mock_db_session.commit.assert_called_once()

def test_delete_event_success(app_b, client_b, mock_db_session, mock_event):
    client, test_user = client_b

    with patch("models.Event.query") as mock_query:
        mock_query.filter_by.return_value.first_or_404.return_value = mock_event
        response = client.delete(f'/api/events/{mock_event.id}')

    assert response.status_code == 200
    mock_db_session.delete.assert_called_once_with(mock_event)
    mock_db_session.commit.assert_called_once()

def test_delete_event_not_found(app_b, client_b, mock_db_session, mock_event):
    client, test_user = client_b

    with app_b.app_context():
        with patch("models.Event.query") as mock_query:
            mock_query.filter_by.return_value.first_or_404.side_effect = NotFound()
            response = client.delete(f'/api/events/{mock_event.id}')

    assert response.status_code == 404
    mock_db_session.delete.assert_not_called()
    mock_db_session.commit.assert_not_called()