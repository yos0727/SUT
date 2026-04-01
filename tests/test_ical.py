import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO
from app import create_app 
from icalendar import Calendar as RealCalendar
'''
UnitTest 21
Mock Query 回傳 2 個事件.驗證 cal.add_component 被呼叫剛好 2 次.

系統能正確將資料庫中的多筆事件, 全數且無漏網地打包進匯出的 .ics 檔案中.
'''
@pytest.fixture
def app():
    _app = create_app()
    _app.config.update({"TESTING": True, "LOGIN_DISABLED": True})
    yield _app

@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client

def test_export_ical_success(client, app):
    # 準備 2 個模擬事件
    event1 = MagicMock()
    event1.title = "Event 1"
    event1.start = "2024-01-01"
    event1.end = "2024-01-01"
    event1.time = "10:00"
    event1.desc = "Description 1"

    event2 = MagicMock()
    event2.title = "Event 2"
    event2.start = "2024-01-02"
    event2.end = "2024-01-02"
    event2.time = None  # 測試程式碼中處理 None 的邏輯
    event2.desc = None

    mock_events = [event1, event2]

    with app.app_context():
        with patch('routes.events_api.Calendar') as MockCalendarClass:
            # 建立一個真實的 Calendar 物件
            real_cal = RealCalendar()
            # 用於監視add_component
            spy_cal = MagicMock(wraps=real_cal)
            MockCalendarClass.return_value = spy_cal
        # Patch 其他依賴
            with patch('routes.events_api.current_user') as mock_user:
                mock_user.id = 1

                with patch('routes.events_api.Event.query') as mock_query:
                    
                    mock_query.filter_by.return_value.all.return_value = mock_events
                    # 執行請求
                    response = client.get('/api/events/export')
                    ical_content = response.data.decode('utf-8')

                    assert response.status_code == 200
                        
                    assert spy_cal.add_component.call_count == 2

                    assert "PRODID:-//My Flask Calendar App//" in ical_content
                    assert "VERSION:2.0" in ical_content
                        
                    # 應該出現 VEVENT 關鍵字
                    assert "BEGIN:VEVENT" in ical_content
                    assert "END:VEVENT" in ical_content

                    # 應該出現 event1, event2
                    assert "SUMMARY:Event 1" in ical_content
                    assert "DESCRIPTION:Description 1" in ical_content
                    assert "DTSTART:20240101" in ical_content

                    assert "SUMMARY:Event 2" in ical_content
                    assert "DESCRIPTION:" in ical_content
                    assert "DTSTART:20240102" in ical_content

                    # 驗證 Response Header
                    assert response.headers["Content-Type"].startswith('text/calendar')
                    assert "attachment; filename=my_calendar.ics" in response.headers["Content-Disposition"]


'''
UnitTest 22
Mock Query 回傳空陣列.驗證產出的 .ics 檔只有 Header 沒有 VEVENT.

當資料庫沒有任何事件時, 系統仍能順利產出結構正確但不含行程的 .ics 空檔案.
'''
def test_export_empty_db(client, app):

    with app.app_context():
        # Mock 登錄使用者
        with patch('routes.events_api.current_user') as mock_user:
            mock_user.id = 99
            
            # Mock 資料庫查詢回傳「空陣列」
            with patch('routes.events_api.Event.query') as mock_query:
                mock_query.filter_by.return_value.all.return_value = []

                # 執行請求
                response = client.get('/api/events/export')

                assert response.status_code == 200
                
                # 將 bytes 轉為字串方便檢查
                ical_content = response.data.decode('utf-8')

                # 驗證 Header 資訊是否正確
                assert "PRODID:-//My Flask Calendar App//" in ical_content
                assert "VERSION:2.0" in ical_content
                
                # 不應該出現 VEVENT 關鍵字
                assert "BEGIN:VEVENT" not in ical_content
                assert "END:VEVENT" not in ical_content
                
                # 驗證 Response Header
                assert response.headers["Content-Type"].startswith('text/calendar')
                assert "attachment; filename=my_calendar.ics" in response.headers["Content-Disposition"]

'''
UnitTest 23
Mock Calendar.from_ical 回傳 5 個元件.驗證 db.session.add 被呼叫剛好 5 次.

系統能正確解析使用者上傳的 .ics 檔案, 並將裡面的行程全數寫入資料庫中.
'''
def test_import_ical_success(client, app):
    # 模擬 5 個 VEVENT 元件 
    mock_components = []
    for i in range(5):
        comp = MagicMock()
        comp.name = "VEVENT"
        # 模擬 component.get('summary') 等行為
        comp.get.side_effect = lambda key, default=None: {
            'summary': f'Event {i}',
            'dtstart': MagicMock(dt=MagicMock()), # 模擬 .get('dtstart').dt
            'dtend': None,
            'description': f'Desc {i}'
        }.get(key, default)
        mock_components.append(comp)

    # 開始 Mock
    with app.app_context():
        # Patch Calendar 類別
        with patch('routes.events_api.Calendar') as MockCalendar:
            # 讓 from_ical 回傳一個模擬的 cal 物件
            mock_cal = MockCalendar.from_ical.return_value
            # 讓 cal.walk() 回傳我們準備好的 5 個元件
            mock_cal.walk.return_value = mock_components

            # Patch SQLAlchemy 的 db.session
            with patch('routes.events_api.db.session') as mock_session, \
                 patch('routes.events_api.current_user') as mock_user:
                
                mock_user.id = 1
                
                # 模擬檔案上傳並發送 POST 請求
                data = {
                    'file': (BytesIO(b"fake ical content"), 'test.ics')
                }
                response = client.post('/api/events/import', data=data, content_type='multipart/form-data')

                assert response.status_code == 200
                assert response.get_json()['message'] == 'Import successful'
                
                assert mock_session.add.call_count == 5
                
                # 驗證最後有執行 commit
                mock_session.commit.assert_called_once()

'''
UnitTest 24
不夾帶檔案發送 POST.驗證回傳 400, 且 db.session.add 呼叫 0 次.

系統會成功阻擋未夾帶檔案的匯入 API 請求, 且不會對資料庫進行任何操作.
'''
def test_import_ical_empty(client, app):
    # 開始 Mock
    with app.app_context():
        # Patch SQLAlchemy 的 db.session
        with patch('routes.events_api.db.session') as mock_session, \
             patch('routes.events_api.current_user') as mock_user:
                
            mock_user.id = 1
                
            # 模擬空檔案上傳並發送 POST 請求
            data = {}
            response = client.post('/api/events/import', data=data, content_type='multipart/form-data')

            assert response.status_code == 400
            assert response.get_json()['error'] == 'No file part'
                
            assert mock_session.add.call_count == 0

'''
UnitTest 25
傳送損壞的 ics 內容, Mock from_ical 拋出錯誤, 驗證 db.session.commit 呼叫 0 次.

系統遇到損壞或格式錯誤的匯入檔時, 能安全中斷處理過程, 絕不污染現有資料庫.
'''
def test_import_invalid_file(client, app):
    with app.app_context():
        with patch('routes.events_api.Calendar.from_ical') as mock_from_ical:
            # 模擬 from_ical 回傳了一個物件, 但它的 walk() 是空列表
            mock_cal = MagicMock()
            mock_cal.walk.return_value = [] 
            mock_from_ical.return_value = mock_cal

            with patch('routes.events_api.db.session') as mock_session:
                # 傳送爛資料
                data = {'file': (BytesIO(b"garbage content"), 'bad.ics')}
                response = client.post('/api/events/import', data=data, content_type='multipart/form-data')

                assert response.status_code == 200
                mock_session.add.assert_not_called()
                # 這裡會執行到 commit, 但因為沒 add 任何東西, 所以資料庫維持原樣
                mock_session.commit.assert_called_once()