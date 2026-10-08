# =======================================================================================
# settings shares tests:  uv run python -m unittest discover -s tests
# =======================================================================================
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from itertools import combinations
from pathlib import Path
from unittest import mock

from autokeys import shares

SETTINGS = b'credentials:\n  aa:\n    user: aa-user\n    pass: aa-pass\n    sites: []\n'


class SharesTest(unittest.TestCase):
    def test_any_needed_shares_open(self):
        stamp = shares.stamp_from_pin('1234')
        parts = shares.split(SETTINGS, stamp, 4, 2)
        for group in combinations(parts, 2):
            self.assertEqual(shares.join(group, stamp), SETTINGS)

    def test_shares_hide_the_settings(self):
        for part in shares.split(SETTINGS, shares.new_stamp(), 3, 2):
            self.assertNotIn(b'pass', part)

    def test_pin(self):
        self.assertEqual(shares.stamp_from_pin('1234'), shares.stamp_from_pin('1234'))
        parts = shares.split(SETTINGS, shares.stamp_from_pin('1234'), 2, 2)
        with self.assertRaises(shares.StampError):
            shares.join(parts, shares.stamp_from_pin('4321'))

    def test_missing_shares(self):
        parts = shares.split(SETTINGS, shares.new_stamp(), 3, 3)
        with self.assertRaises(shares.SharesError):
            shares.join(parts[:2] + parts[:1], shares.new_stamp())

    def test_different_splits(self):
        stamp = shares.new_stamp()
        first = shares.split(SETTINGS, stamp, 2, 2)
        second = shares.split(SETTINGS, stamp, 2, 2)
        with self.assertRaises(shares.ShareError):
            shares.join([first[0], second[1]], stamp)

    def test_invalid_split(self):
        for count, needed in [(2, 3), (3, 0), (20, 17)]:
            with self.assertRaises(shares.ShareError):
                shares.split(SETTINGS, shares.new_stamp(), count, needed)

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'config.yml').write_bytes(SETTINGS)
            with redirect_stdout(StringIO()):
                shares.main(['stamp', str(tmp / 'my.stamp')])
                shares.main(['split', str(tmp / 'config.yml'), '--stamp', str(tmp / 'my.stamp')])
            self.assertEqual(os.stat(tmp / 'my.stamp').st_mode & 0o777, 0o600)
            out = StringIO()
            out.buffer = mock.Mock()
            with redirect_stdout(out):
                shares.main(['join', str(tmp / 'config.yml.3.share'),
                             str(tmp / 'config.yml.1.share'), '--stamp', str(tmp / 'my.stamp')])
            out.buffer.write.assert_called_once_with(SETTINGS)
            with mock.patch.dict(os.environ, {'AUTOKEYS_PIN': '99'}), self.assertRaises(SystemExit):
                shares.main(['join', str(tmp / 'config.yml.1.share'), str(tmp / 'config.yml.2.share')])


if __name__ == '__main__':
    unittest.main()
