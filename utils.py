from datetime import datetime

def get_day_events(events, date_str):
    day_events = []
    current_date = datetime.strptime(date_str, "%Y-%m-%d")
    for e in events:
        start = datetime.strptime(e["start"], "%Y-%m-%d")
        end = datetime.strptime(e["end"], "%Y-%m-%d")
        if start <= current_date <= end:
            day_events.append(e)
    return day_events

def serialize_event(e):
    return {
        "id": e.id,
        "title": e.title,
        "start": e.start,
        "end": e.end,
        "time": e.time,
        "desc": e.desc,
        "color": e.color
    }