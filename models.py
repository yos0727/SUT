from extensions import db
from flask_login import UserMixin

# 新增 User 模型，並繼承 UserMixin 以取得 is_authenticated 等屬性
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    
    # 建立與 Event 的一對多關聯
    events = db.relationship('Event', backref='author', lazy=True)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    start = db.Column(db.String(10), nullable=False)
    end = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(5))
    desc = db.Column(db.Text)
    color = db.Column(db.String(7), default='#ffcccc')
    is_all_day = db.Column(db.Boolean, default=False)
    recurrence = db.Column(db.String(100), nullable=True)
    
    # 新增：外鍵關聯到 User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)