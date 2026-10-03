from datetime import datetime, timezone
from uuid import uuid4
from . import repository as repo
from .errors import InvalidRequest, SoldOut
from .models import Reservation
from .pricing import quote

def utc_now():
    return datetime.now(timezone.utc)

def iso_time(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidRequest('clock must be timezone aware')
    return value.astimezone(timezone.utc).isoformat()

def validate_customer(customer_id):
    if not isinstance(customer_id,str) or not customer_id.strip():
        raise InvalidRequest('customer must be a nonempty string')

def book_in_transaction(connection, event_id, customer_id, seats, now, *, member=False, coupon=None):
    validate_customer(customer_id)
    item=repo.event(connection,event_id)
    starts=datetime.fromisoformat(item['starts_at'])
    if datetime.fromisoformat(now) >= starts:
        raise InvalidRequest('event has already started')
    price=quote(item['unit_price'],seats,member=member,coupon=coupon)
    if repo.available(connection,event_id) < seats:
        raise SoldOut('insufficient seats')
    result=Reservation(str(uuid4()),event_id,customer_id,seats,price.total,'confirmed',now)
    connection.execute('INSERT INTO reservations VALUES(?,?,?,?,?,?,?)',
                       (result.id,result.event_id,result.customer_id,result.seats,result.total,result.status,result.created_at))
    repo.audit(connection,'reservation.created',result.id,{'seats':seats},now)
    return result

class BookingService:
    def __init__(self, db, clock=utc_now):
        self.db=db
        self.clock=clock

    def book(self,event_id,customer_id,seats,*,member=False,coupon=None):
        now=iso_time(self.clock())
        with self.db.transaction() as connection:
            return book_in_transaction(connection,event_id,customer_id,seats,now,member=member,coupon=coupon)

    def get(self,reservation_id):
        connection=self.db.connect()
        try:
            return repo.reservation(connection,reservation_id)
        finally:
            connection.close()

    def available(self,event_id):
        connection=self.db.connect()
        try:
            return repo.available(connection,event_id)
        finally:
            connection.close()
