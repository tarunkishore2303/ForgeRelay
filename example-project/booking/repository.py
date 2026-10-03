import json
from .errors import NotFound
from .models import Reservation

def event(connection, event_id):
    row=connection.execute('SELECT * FROM events WHERE id=?',(event_id,)).fetchone()
    if row is None:
        raise NotFound('event does not exist')
    return row

def available(connection, event_id):
    item=event(connection,event_id)
    used=connection.execute("SELECT COALESCE(SUM(seats),0) FROM reservations WHERE event_id=? AND status='confirmed'",(event_id,)).fetchone()[0]
    return item['capacity']-used

def reservation(connection, reservation_id):
    row=connection.execute('SELECT * FROM reservations WHERE id=?',(reservation_id,)).fetchone()
    if row is None:
        raise NotFound('reservation does not exist')
    return Reservation.from_row(row)

def audit(connection, action, entity_id, payload, now):
    connection.execute('INSERT INTO audit(action,entity_id,payload,created_at) VALUES(?,?,?,?)',
                       (action,entity_id,json.dumps(payload,sort_keys=True),now))
