# test_auth
import pytest
from unittest import mock
from app import create_app
from models import User

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_user():
    with mock.patch("routes.auth.User") as m:
        yield m

@pytest.fixture
def mock_db():
    with mock.patch("routes.auth.db.session") as m:
        yield m

@pytest.fixture
def mock_login_user():
    with mock.patch("routes.auth.login_user") as m:
        yield m

@pytest.fixture
def mock_logout_user():
    with mock.patch("routes.auth.logout_user") as m:
        yield m

@pytest.fixture
def mock_redirect():
    with mock.patch("routes.auth.redirect") as m:
        yield m

@pytest.fixture
def mock_url_for():
    with mock.patch("routes.auth.url_for") as m:
        yield m

@pytest.fixture
def mock_flash():
    with mock.patch("routes.auth.flash") as m:
        yield m

@pytest.fixture
def mock_render_template():
    with mock.patch("routes.auth.render_template") as m:
        yield m

@pytest.fixture
def mock_check_pw():
    with mock.patch("routes.auth.check_password_hash") as m:
        yield m

def test_register_success(mock_user, mock_db, mock_login_user, mock_redirect, mock_url_for, client):
    mock_user.query.filter_by.return_value.first.return_value = None
    mock_url_for.return_value = '/calendar'
    
    response = client.post("/register", data={
        'username': 'newuser',
        'password': 'newpassword'
    })
    
    mock_user.query.filter_by.assert_called_with(username="newuser")
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_login_user.assert_called_once()
    mock_redirect.assert_called_with('/calendar')


def test_register_duplicate(client, mock_user, mock_url_for, mock_flash, mock_db, mock_redirect):
    mock_user.query.filter_by.return_value.first.return_value = mock.Mock()
    mock_url_for.return_value = '/register'
    response = client.post("/register", data={
        'username': 'existeduser',
        'password': 'existedpassword'
    })
    mock_flash.assert_called_once_with('Username already exists.')
    mock_db.session.add.assert_not_called()
    mock_db.session.commit.assert_not_called()
    mock_redirect.assert_called_with('/register')

def test_login_success(client, mock_user, mock_check_pw, mock_url_for, mock_login_user, mock_redirect):
    fake_user = mock.Mock()
    mock_user.query.filter_by.return_value.first.return_value = fake_user
    mock_check_pw.return_value = True
    mock_url_for.return_value = '/calendar'
    response = client.post("/login", data={
        'username': 'existeduser',
        'password': 'existedpassword'
    })

    mock_check_pw.assert_called_once_with(fake_user.password, 'existedpassword')
    mock_login_user.assert_called_once_with(fake_user)
    mock_redirect.assert_called_with('/calendar')

def test_login_wrong_pwd(client, mock_user, mock_check_pw, mock_render_template, mock_flash):
    fake_user = mock.Mock()
    mock_user.query.filter_by.return_value.first.return_value = fake_user
    mock_check_pw.return_value = False
    response = client.post("/login", data={
        'username': 'existeduser',
        'password': 'wrongpassword'
    })

    mock_check_pw.assert_called_once_with(fake_user.password,'wrongpassword')
    mock_flash.assert_called_once_with('Login failed. Check username and password.')
    mock_render_template.assert_called_with('login.html')

def test_login_not_found(client, mock_user, mock_render_template, mock_flash):
    mock_user.query.filter_by.return_value.first.return_value = None

    response = client.post("/login", data={
        'username': 'existeduser',
        'password': 'wrongpassword'
    })

    mock_flash.assert_called_once_with('Login failed. Check username and password.')
    mock_render_template.assert_called_with('login.html')
