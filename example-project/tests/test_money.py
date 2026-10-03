"""Independent checks, deliberately excluded from worker source context."""
import unittest
from booking.money import format_cents
from booking.errors import InvalidRequest

class MoneyTests(unittest.TestCase):
    def test_zero_and_fractional_amounts(self):
        for value,expected in [(0,'0.00'),(1,'0.01'),(9,'0.09'),(99,'0.99'),(100,'1.00'),(101,'1.01')]:
            with self.subTest(value=value):self.assertEqual(format_cents(value),expected)

    def test_negative_amounts(self):
        for value,expected in [(-1,'-0.01'),(-99,'-0.99'),(-100,'-1.00'),(-12345,'-123.45')]:
            with self.subTest(value=value):self.assertEqual(format_cents(value),expected)

    def test_large_integer_precision(self):
        self.assertEqual(format_cents(100000000000000000001),'1000000000000000000.01')

    def test_invalid_types(self):
        for value in [True,False,None,'101',1.01,[],{}]:
            with self.subTest(value=value),self.assertRaises(InvalidRequest):format_cents(value)
