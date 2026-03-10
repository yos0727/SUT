## 檔案結構
```
calendar_app/
├── app.py                  # 程式進入點 (初始化 Flask、DB、載入設定)
├── config.py               # 設定檔 (資料庫 URI、Secret Key 等)
├── models.py               # SQLAlchemy 資料庫模型 (User, Event)
├── utils.py                # 輔助函式 (日期計算、iCal 轉換等)
├── routes/                 # API 與路由模組化 (Blueprints)
│   ├── __init__.py
│   ├── auth.py             # 註冊、登入、身分驗證 API
│   ├── events.py           # 事件 CRUD (RESTful API)
│   └── views.py            # 負責回傳首頁 index.html 的主要路由
├── static/                 # 靜態資源 (前端程式碼)
│   ├── css/
│   │   └── style.css       # 抽離原本寫在 HTML 裡的 CSS
│   └── js/
│       ├── api.js          # 負責使用 fetch 與後端溝通
│       └── calendar.js     # 處理拖曳、視圖切換、Modal 邏輯與 DOM 渲染
└── templates/
    ├── base.html           # 基礎模板 (引入共用的 CSS/JS)
    ├── index.html          # 主日曆頁面 (SPA 進入點，不再使用 Jinja 迴圈渲染天數)
    └── login.html          # 註冊與登入頁面
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
