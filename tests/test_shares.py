# =======================================================================================
# settings shares tests:  uv run python -m unittest discover -s tests
#   (split, join and edit themselves are tested in codec-share)
# =======================================================================================
import os
import shlex
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from codec_share.shares import join, read_shares, stamp_from_pin

from autokeys import shares

SETTINGS = b'credentials:\n  aa:\n    user: aa-user\n    pass: aa-pass\n    sites: []\n'


def editor(code):
    script = Path(tempfile.mkdtemp()) / 'editor.py'
    script.write_text(f'import sys\npath = sys.argv[1]\n{code}\n')
    return shlex.join([sys.executable, str(script)])


class SettingsSharesTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.settings = self.folder / 'config.yml'
        self.settings.write_bytes(SETTINGS)
        self.env = mock.patch.dict(os.environ, {'AUTOKEYS_PIN': '1234'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def share(self, *args):
        with redirect_stdout(StringIO()):
            shares.main(list(map(str, args)))

    def test_split_uses_the_autokeys_pin(self):
        self.share('split', self.settings)
        parts = read_shares(self.folder.glob('config.yml.*.share'))
        self.assertEqual(len(parts), 3)
        self.assertEqual(join(parts[:2], stamp_from_pin('1234')), SETTINGS)

    def test_split_rejects_invalid_settings(self):
        self.settings.write_bytes(b'- not\n- settings\n')
        with self.assertRaises(SystemExit):
            self.share('split', self.settings)
        self.assertEqual(list(self.folder.glob('*.share')), [])

    def test_edit_updates_the_shares(self):
        self.share('split', self.settings)
        self.share('edit', self.folder / 'config.yml.1.share', self.folder / 'config.yml.2.share',
                   '-e', editor("open(path, 'ab').write(b'  bb:\\n    user: bb\\n')"))
        parts = read_shares([self.folder / 'config.yml.3.share', self.folder / 'config.yml.1.share'])
        self.assertEqual(join(parts, stamp_from_pin('1234')),
                         SETTINGS + b'  bb:\n    user: bb\n')

    def test_edit_drops_invalid_settings(self):
        self.share('split', self.settings)
        before = read_shares(sorted(self.folder.glob('*.share')))
        with mock.patch('builtins.input', return_value='n'):
            self.share('edit', self.folder / 'config.yml.1.share',
                       self.folder / 'config.yml.2.share',
                       '-e', editor("open(path, 'w').write('a: [unclosed')"))
        self.assertEqual(read_shares(sorted(self.folder.glob('*.share'))), before)

    def test_service_loads_shares(self):
        self.share('split', self.settings)
        sys.modules.setdefault('pynput', mock.MagicMock())
        sys.modules.setdefault('pyperclip', mock.MagicMock())
        from autokeys import service
        parser = service.ArgumentParser()
        parser.add_argument('settings', nargs='+')
        shares.add_stamp_arguments(parser)
        arguments = parser.parse_args(
            [str(self.folder / 'config.yml.3.share'), str(self.folder / 'config.yml.2.share')])
        self.assertEqual(service.load_settings(arguments)['credentials']['aa']['user'], 'aa-user')


if __name__ == '__main__':
    unittest.main()
