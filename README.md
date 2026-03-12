## 檔案結構
```
SUT/
├── app.py                  # 程式進入點 (初始化 Flask、DB、載入設定)
├── config.py               # 設定檔 (資料庫 URI、Secret Key 等)
├── models.py               # SQLAlchemy 資料庫模型 (User, Event)
├── utils.py                # 輔助函式 (日期計算、iCal 轉換等)
├── extensions.py           # 資料庫與身分驗證功能模組化
├── routes/                 # API 與路由模組化 (Blueprints)
│   ├── auth.py             # 註冊、登入、身分驗證 API
│   ├── events.py           # 事件 CRUD (RESTful API)
│   └── views.py            # 負責回傳首頁 calendar.html 的主要路由
└── templates/
    ├── add_event.html      # 增加事件頁面
    ├── calendar.html       # 主日曆頁面 (SPA 進入點)
    ├── register.html       # 註冊頁面
    └── login.html          # 登入頁面
```


## 使用技術

**前端技術 (Frontend)**

* **核心語言**：HTML, CSS, JavaScript
* **非同步通訊**：Fetch API (AJAX) 負責與後端進行 JSON 資料交換


**後端技術 (Backend)**

* **核心語言**：Python
* **網頁框架**：Flask 
* **身分驗證與安全**：Flask-Login (Session 與狀態管理)、Werkzeug.security (密碼雜湊加密)
* **資料庫 ORM**：Flask-SQLAlchemy (物件關聯對映)



**資料庫 (Database)**
* SQLite (輕量級關聯式資料庫，適合本地開發與輕度部署)
