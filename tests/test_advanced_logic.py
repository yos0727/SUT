import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app import create_app
from utils import serialize_event

'''
UnitTest 18
測試重複事件剛好落在展開視窗 (window_end) 的最後一天, 驗證是否被正確包含 (Return True).

系統能精準計算並包含「剛好壓在未來兩年展開極限最後一天」的重複事件, 沒有差一錯誤.
'''
@pytest.fixture
def app():
    # 呼叫函式產生 Flask 實例
    _app = create_app()
    _app.config.update({
        "TESTING": True,
        "LOGIN_DISABLED": True,
    })
    yield _app

@pytest.fixture
def client(app):
    # 使用產生出來的 app 建立測試客戶端
    with app.test_client() as client:
        yield client

def test_rrule_boundary_date(client, app):
    # 定義一個固定的時間
    frozen_now = datetime(2024, 1, 1, 10, 0, 0)

    # 邊界設定
    boundary_date = frozen_now + timedelta(days=730)
    boundary_date_str = boundary_date.strftime("%Y-%m-%d")

    # MOCK 事件
    mock_event = MagicMock()
    mock_event.id = 1
    mock_event.user_id = 123
    mock_event.start = "2024-01-01"
    mock_event.end = "2024-01-01"
    mock_event.recurrence = 'FREQ=DAILY'

    with app.app_context():

        with patch('routes.events_api.current_user') as mock_user:
            mock_user.id = 1
                
            with patch('routes.events_api.datetime') as mock_dt:
                mock_dt.now.return_value = frozen_now
                mock_dt.strptime = datetime.strptime
                    
                with patch('routes.events_api.Event.query') as mock_query:
                    mock_query.filter_by.return_value.all.return_value = [mock_event]
                        
                    with patch('routes.events_api.serialize_event', side_effect=lambda e: {"start": e.start}):
                        # 呼叫請求
                        response = client.get('/api/events/')
                            
                        assert response.status_code == 200
                        data = response.get_json()

                        assert any(item['start'] == boundary_date_str for item in data)

'''
UnitTest 19
呼叫 serialize_event, 傳入 Mock Event, 驗證 Dictionary 對應是否 100% 準確.

系統能將資料庫的 Event 物件, 精準無誤地轉換為前端 API 需要的 JSON 字典格式.
'''
def test_serialize_event():
    mock_event = MagicMock()
    mock_event.id = 1
    mock_event.title = 'test'
    mock_event.start = '2024-01-01'
    mock_event.end = '2024-01-01'
    mock_event.time = '10:10'
    mock_event.desc = 'Nothing'
    mock_event.color = '#ffcccc'
    mock_event.is_all_day = False
    mock_event.recurrence = ''

    assert serialize_event(mock_event) == {
        "id": 1,
        "title": 'test',
        "start": '2024-01-01',
        "end": '2024-01-01',
        "time": '10:10',
        "desc": 'Nothing',
        "color": '#ffcccc',
        "is_all_day": False,
        "recurrence": ''
    }
'''
UnitTest 20
傳入欄位皆為 None 的 Mock Event, 驗證序列化不報錯 (Return True).

系統在轉換所有欄位皆為空值的極端事件物件時, 依然能順利執行而不會發生崩潰.
'''
def test_serialize_empty():
    mock_event = MagicMock()
    mock_event.id = None
    mock_event.title = None
    mock_event.start = None
    mock_event.end = None
    mock_event.time = None
    mock_event.desc = None
    mock_event.color = None
    mock_event.is_all_day = None
    mock_event.recurrence = None

    assert serialize_event(mock_event)