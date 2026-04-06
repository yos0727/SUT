from flask import Blueprint, request, jsonify, Response
from flask_login import login_required, current_user
from models import Event
from extensions import db
from utils import serialize_event
from icalendar import Calendar, Event as IcalEvent
from datetime import datetime, timedelta
from dateutil.rrule import rrulestr

events_api = Blueprint('events_api', __name__, url_prefix='/api/events')


@events_api.route('/', methods=['GET'])
@login_required
def get_events():
    events = Event.query.filter_by(user_id=current_user.id).all()
    result = []
    
    # 定義展開的時間視窗 (避免無限重複的事件導致記憶體耗盡，這裡設定抓取過去1年到未來2年)
    now = datetime.now()
    window_start = now - timedelta(days=400)
    window_end = now + timedelta(days=1000)
    for e in events:
        if e.recurrence:
            try:
                # 解析事件的原始開始與結束日期
                base_start = datetime.strptime(e.start, "%Y-%m-%d")
                base_end = datetime.strptime(e.end, "%Y-%m-%d")
                duration = base_end - base_start

                # 實作看前一年, 只有Yearly時才會往前看
                if(e.recurrence == "FREQ=YEARLY"):
                    temp_date = e.start.split('-')
                    start_date = f"{int(temp_date[0]) - 1}-{int(temp_date[1])}-{int(temp_date[2])}"
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                    rule = rrulestr(e.recurrence, dtstart=start_date)
                else:
                    # 根據 RRULE 展開日期
                    # dtstart 應為事件的開始時間 (base_start)，使用 base_end 會造成展開時機錯誤或重複
                    rule = rrulestr(e.recurrence, dtstart=base_start)
                instances = rule.between(window_start, window_end, inc=True)
                for inst in instances:
                    inst_end = inst + duration
                    # 複製原始事件的字典，並覆寫 start 與 end
                    ev_dict = serialize_event(e)
                    ev_dict['start'] = inst.strftime("%Y-%m-%d")
                    ev_dict['end'] = inst_end.strftime("%Y-%m-%d")
                    result.append(ev_dict) 
            except Exception as ex:
                # 若 RRULE 解析失敗，退回顯示單一事件
                result.append(serialize_event(e))
        else:
            result.append(serialize_event(e))
            
    return jsonify(result)

@events_api.route('/', methods=['POST'])
@login_required
def create_event():
    try:
        data = request.json or request.form

        # 確保 is_all_day 能夠正確轉換為布林值
        is_all_day_val = data.get('is_all_day', False)
        if isinstance(is_all_day_val, str):
            is_all_day = is_all_day_val.lower() in ['true', '1']
        else:
            is_all_day = bool(is_all_day_val)

        new_event = Event(
            title=data.get('title') if data.get('title') else "(no title)",
            start=data.get('start'),
            end=data.get('end'),
            time=data.get('time', ''),
            desc=data.get('desc', ''),
            color=data.get('color', '#ffcccc'),
            is_all_day=is_all_day,
            recurrence=data.get('recurrence', ''), # 確保這裡有接收 recurrence
            user_id=current_user.id # 綁定目前登入的使用者
        )
        db.session.add(new_event)
        db.session.commit()

        return jsonify(serialize_event(new_event)), 201

    except Exception as ex:
        return jsonify({"error": "Internal Server Error"}), 500


@events_api.route('/<int:event_id>', methods=['PUT'])
@login_required
def update_event(event_id):
    # 確保只能修改自己的事件
    event = Event.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    data = request.json
    
    if 'title' in data: event.title = data['title']
    if 'start' in data: event.start = data['start']
    if 'end' in data: event.end = data['end']
    if 'desc' in data: event.desc = data['desc']
    if 'color' in data: event.color = data['color']
    
    # 修正這裡：加入 is_all_day 的更新邏輯
    if 'is_all_day' in data:
        # JSON 傳遞過來可能是 boolean，我們確保它正確轉換
        event.is_all_day = bool(data['is_all_day'])
        
        # 如果切換成全天事件，順便把時間清空，保持資料乾淨
        if event.is_all_day:
            event.time = ""
        elif 'time' in data:
            event.time = data['time']
    elif 'time' in data:
        event.time = data['time']
    # 處理重複規則的更新
    if 'recurrence' in data: event.recurrence = data['recurrence']
    db.session.commit()

    if not (event.is_all_day or event.time):
        print("ERROR!")
        return jsonify({'error': '事件必須是全天或具有時間'}), 400
    else:
        print("nothing happen")

    return jsonify(serialize_event(event)), 200

@events_api.route('/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    event = Event.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    db.session.delete(event)
    db.session.commit()
    return jsonify({'message': 'deleted'}), 200

@events_api.route('/export', methods=['GET'])
@login_required
def export_ical():
    cal = Calendar()
    cal.add('prodid', '-//My Flask Calendar App//')
    cal.add('version', '2.0')

    events = Event.query.filter_by(user_id=current_user.id).all()
    for e in events:
        ie = IcalEvent()
        ie.add('summary', e.title or "(no title)")
        
        # 處理日期與時間格式
        time_str = e.time if e.time else '00:00'
        start_dt = datetime.strptime(f"{e.start} {time_str}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{e.end} {time_str}", "%Y-%m-%d %H:%M")
        
        ie.add('dtstart', start_dt)
        ie.add('dtend', end_dt)
        # 如果有 recurrence，寫入 RRULE
        if getattr(e, 'recurrence', None):
            try:
                ie.add('rrule', e.recurrence)
            except Exception:
                # 如果無法直接加入，嘗試以原始字串方式加入
                ie['RRULE'] = str(e.recurrence)
        # 將顏色寫入自訂欄位，匯入時會讀出 X-COLOR
        if getattr(e, 'color', None):
            try:
                ie.add('X-COLOR', e.color)
            except Exception:
                ie['X-COLOR'] = str(e.color)
        if e.desc:
            ie.add('description', e.desc)
            
        cal.add_component(ie)

    return Response(
        cal.to_ical(),
        mimetype='text/calendar',
        headers={"Content-disposition": "attachment; filename=my_calendar.ics"}
    )

@events_api.route('/import', methods=['POST'])
@login_required
def import_ical():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        try:
            cal = Calendar.from_ical(file.read())
        except ValueError:
            return jsonify({'error': 'Invalid iCal format'}), 400
        for component in cal.walk():
            if component.name == "VEVENT":
                # 避免 summary 或 description 回傳 None 被轉成 'None' 字串，提供合理預設
                raw_summary = component.get('summary')
                summary = str(raw_summary) if raw_summary is not None else "(no title)"

                dtstart = component.get('dtstart').dt
                dtend = component.get('dtend').dt if component.get('dtend') else dtstart

                raw_desc = component.get('description')
                description = str(raw_desc) if raw_desc is not None else ""

                # 讀取 RRULE（重複規則）與自訂顏色欄位（若有）
                raw_rrule = component.get('rrule') or component.get('RRULE')
                recurrence = ""
                if raw_rrule:
                    try:
                        # raw_rrule 有可能是 dict-like (vRecur)，或其他型態
                        if isinstance(raw_rrule, dict):
                            parts = []
                            for k, v in raw_rrule.items():
                                # v 可能為 list
                                if isinstance(v, (list, tuple)):
                                    vals = []
                                    for x in v:
                                        if hasattr(x, 'strftime'):
                                            vals.append(x.strftime('%Y%m%dT%H%M%S'))
                                        else:
                                            vals.append(str(x))
                                    parts.append(f"{k}={','.join(vals)}")
                                else:
                                    parts.append(f"{k}={str(v)}")
                            recurrence = ';'.join(parts)
                        else:
                            recurrence = str(raw_rrule)
                    except Exception:
                        recurrence = str(raw_rrule)

                raw_color = None
                # 優先取得自訂屬性 X-COLOR（export 時我們會寫入 X-COLOR）
                try:
                    raw_color = component.get('x-color') or component.get('X-COLOR') or component.get('color')
                except Exception:
                    raw_color = None
                color_val = str(raw_color) if raw_color is not None else None

                # 簡單的格式轉換 (忽略複雜的時區，直接轉字串)
                start_date = dtstart.strftime("%Y-%m-%d") if hasattr(dtstart, 'strftime') else str(dtstart)
                end_date = dtend.strftime("%Y-%m-%d") if hasattr(dtend, 'strftime') else str(dtend)
                time_str = dtstart.strftime("%H:%M") if hasattr(dtstart, 'strftime') and len(str(dtstart)) > 10 else ""

                # 檢查是否已存在相同的事件 (由 user_id, title, start, end 判斷)
                exists = Event.query.filter_by(user_id=current_user.id, title=summary if summary else "(no title)", start=start_date, end=end_date).first()
                if exists:
                    # 若存在，嘗試補上缺少的欄位（例如 recurrence, color, desc, time）
                    updated = False
                    if not exists.recurrence and recurrence:
                        exists.recurrence = recurrence
                        updated = True
                    if not exists.color and color_val:
                        exists.color = color_val
                        updated = True
                    if not exists.desc and description:
                        exists.desc = description
                        updated = True
                    if (not exists.time or exists.time == '') and time_str:
                        exists.time = time_str
                        # 若匯入具有時間，則視為非全天事件
                        exists.is_all_day = False
                        updated = True
                    if updated:
                        db.session.add(exists)
                else:
                    new_event = Event(
                        title=summary if summary else "(no title)",
                        start=start_date,
                        end=end_date,
                        time=time_str,
                        desc=description,
                        color=color_val or '#ffcccc',
                        is_all_day=True if not time_str else False,
                        recurrence=recurrence,
                        user_id=current_user.id
                    )
                    db.session.add(new_event)
        
        db.session.commit()
        return jsonify({'message': 'Import successful'}), 200