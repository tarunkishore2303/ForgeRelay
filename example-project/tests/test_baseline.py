from uuid import uuid4
import unittest
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from booking.db import Database
from booking.catalog import Catalog
from booking.service import BookingService
from booking.errors import SoldOut, InvalidRequest
from booking.pricing import quote

class BaselineTests(unittest.TestCase):
    def setUp(self):
        folder=Path(__file__).resolve().parents[1]/'test-data'
        folder.mkdir(exist_ok=True)
        path=folder/(str(uuid4())+'.sqlite')
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        self.db=Database(path)
        Catalog(self.db).create('event','Workshop',2,1000,'2030-01-02T10:00:00+00:00')
        self.service=BookingService(self.db,lambda:datetime(2030,1,1,tzinfo=timezone.utc))

    def test_persistence(self):
        item=self.service.book('event','alice',1)
        self.assertEqual(self.service.get(item.id),item)
        self.assertEqual(self.service.available('event'),1)

    def test_failed_booking_is_atomic(self):
        with self.assertRaises(SoldOut): self.service.book('event','alice',3)
        connection=self.db.connect()
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute('SELECT COUNT(*) FROM audit').fetchone()[0],0)

    def test_concurrent_last_seats(self):
        def attempt(i):
            try: self.service.book('event',str(i),1); return True
            except SoldOut: return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(attempt,range(4))),2)
        self.assertEqual(self.service.available('event'),0)

    def test_pricing(self):
        self.assertEqual(quote(1000,1).total,1083)
        with self.assertRaises(InvalidRequest): quote(1000,True)
