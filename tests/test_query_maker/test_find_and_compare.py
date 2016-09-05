from backend.query_maker.find_and_compare import match_time_sequence
import functools
import timeit
import unittest


class TestFindAndCompare(unittest.TestCase):

    def test_simple_matches(self):
        f = match_time_sequence

        print(">> backend.query_maker.find_and_compare.match_time_sequence:")

        _str = "t0d11t0d10t0d15"
        _dia, _tim, _exm = [11, 10, 15], [(0, 0), (0, 0)], [(0, 100), (0, 100)]
        self.assertEqual(f(_str, _dia, _tim, _exm), (True, []))
        print("--> n skip, n time, n exam, n future - OK")

        _str = "t0d11t0d10t0d15t0d10t0d15"
        _dia, _tim, _exm = [11, 10, 15], [(0, 0), (0, 0)], [(0, 100), (0, 100)]
        self.assertEqual(f(_str, _dia, _tim, _exm), (True, [10, 15]))
        print("--> n skip, n time, n exam, y future - OK")

        _str = "t200d11t150d10t100d15"
        _dia, _tim, _exm = [11, 10, 15], [(125, 150), (100, 125)], [(1, 1), (1, 1)]
        self.assertEqual(f(_str, _dia, _tim, _exm), (True, []))
        print("--> n skip, y time, y exam, n future - OK")

        _str = "t200d11t150d10t100d15t200d11t122d11t15d10t111d15t1d1"
        _dia, _tim, _exm = [11, 10, 15], [(125, 149), (100, 125)], [(1, 2), (1, 1)]
        self.assertEqual(f(_str, _dia, _tim, _exm), (True, [1]))
        print("--> n skip, y time, y exam, y future - OK")

        _str = "t200d11t10d20t150d10t100d15"
        _dia, _tim, _exm = [11, 10, 15], [(125, 200), (100, 125)], [(2, 2), (1, 30)]
        self.assertEqual(f(_str, _dia, _tim, _exm), (True, []))
        print("--> y skip, y time, y exam, n future - OK")

        _str = "t200d11t10d20t150d10t100d15t0d15t1230d5"
        _dia, _tim, _exm = [11, 10, 15], [(125, 200), (100, 125)], [(2, 2), (1, 30)]
        self.assertEqual(f(_str, _dia, _tim, _exm), (True, [15, 5]))
        print("--> y skip, y time, y exam, y future - OK")