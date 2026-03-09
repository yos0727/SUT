from flask import Flask, render_template, request, redirect
import calendar
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from utils import get_day_events, serialize_event

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
db = SQLAlchemy(app)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    start = db.Column(db.String(10))
    end = db.Column(db.String(10))
    time = db.Column(db.String(5))
    desc = db.Column(db.Text)
    color = db.Column(db.String(7))

with app.app_context():
    db.create_all()


@app.route("/")
def calendar_view():

    year = request.args.get("year", datetime.today().year, type=int)
    month = request.args.get("month", datetime.today().month, type=int)

    pre_year = year - 1 if month == 1 else year
    pre_month = month - 1 if month != 1 else 12

    next_year = year + 1 if month == 12 else year
    next_month = month + 1 if month != 12 else 1

    cal = calendar.monthcalendar(year, month)
    events = Event.query.all()
    events_dict = [serialize_event(e) for e in events]

    return render_template(
        "calendar.html",
        cal=cal,
        month=month,
        year=year,
        pre_year=pre_year,
        pre_month=pre_month,
        next_year=next_year,
        next_month=next_month,
        get_events=get_day_events,
        all_events=events_dict
    )


@app.route("/add_event", methods=["GET", "POST"])
def add_event():

    if request.method == "POST":
        event = Event(
            title=request.form["title"],
            start=request.form["start"],
            end=request.form["end"],
            time=request.form["time"],
            desc=request.form["desc"],
            color=request.form["color"]
        )
        db.session.add(event)
        db.session.commit()

        return redirect("/")

    return render_template("add_event.html")


@app.route("/edit_event", methods=["POST"])
def edit_event():
    event_id = int(request.form["id"])
    event = Event.query.get(event_id)
    if event:
        event.title = request.form["title"]
        event.start = request.form["start"]
        event.end = request.form["end"]
        event.time = request.form["time"]
        event.desc = request.form["desc"]
        event.color = request.form["color"]
        db.session.commit()
        return "ok"
    return "not found", 404

@app.route("/delete_event", methods=["POST"])
def delete_event():
    event_id = int(request.form["id"])
    event = Event.query.get(event_id)
    if event:
        db.session.delete(event)
        db.session.commit()
        return "ok"
    return "not found", 404

if __name__ == "__main__":
    app.run(debug=True)