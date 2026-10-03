from datetime import datetime
from .errors import InvalidRequest
from .service import iso_time

class Catalog:
    def __init__(self,db):
        self.db=db

    def create(self,event_id,title,capacity,unit_price,starts_at):
        if not all(isinstance(v,str) and v.strip() for v in [event_id,title]):
            raise InvalidRequest('event id and title must be nonempty strings')
        if type(capacity) is not int or capacity <= 0 or type(unit_price) is not int or unit_price < 0:
            raise InvalidRequest('invalid inventory or price')
        stamp=iso_time(datetime.fromisoformat(starts_at))
        with self.db.transaction() as connection:
            connection.execute('INSERT INTO events VALUES(?,?,?,?,?)',(event_id,title,capacity,unit_price,stamp))
