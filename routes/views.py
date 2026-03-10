from flask import Blueprint, render_template
from flask_login import login_required

views = Blueprint('views', __name__)

@views.route("/")
@login_required
def calendar_view():
    # 所有的日曆邏輯與事件抓取都交給前端 JavaScript 處理
    return render_template("calendar.html")
