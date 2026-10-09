# =======================================================================================
# settings shares tests:  uv run python -m unittest discover -s tests
#   (split, join and edit themselves are tested in codec-share)
# =======================================================================================
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from codec_share import Stamp, cli, join, load

from autokeys import shares

SETTINGS = b'credentials:\n  aa:\n    user: aa-user\n    pass: aa-pass\n    sites: []\n'
PIN = {'AUTOKEYS_PIN': '1234'}


def editor(code):
    script = Path(tempfile.mkdtemp()) / 'editor.py'
    script.write_text(f'import sys\npath = sys.argv[1]\n{code}\n')
    return shlex.join([sys.executable, str(script)])


class SettingsSharesTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.settings = self.folder / 'config.yml'
        self.settings.write_bytes(SETTINGS)
        self.runner = CliRunner()

    def share(self, *args, ok=True, **kwargs):
        result = self.runner.invoke(cli.main, list(map(str, args)), env=PIN,
                                    obj=shares.OPTIONS, prog_name='autokeys-share', **kwargs)
        if ok:
            self.assertEqual(result.exit_code, 0, result.output)
        return result

    def path(self, index):
        return self.folder / f'config.yml.{index}.share'

    def test_split_uses_the_autokeys_pin(self):
        self.share('split', self.settings)
        self.assertEqual(join(load([self.path(1), self.path(3)]), Stamp.from_pin('1234')),
                         SETTINGS)

    def test_split_rejects_invalid_settings(self):
        self.settings.write_bytes(b'- not\n- settings\n')
        result = self.share('split', self.settings, ok=False)
        self.assertEqual(result.exit_code, 1)
        self.assertIn('invalid file: settings must be a yaml mapping', result.output)
        self.assertEqual(list(self.folder.glob('*.share')), [])

    def test_edit_updates_the_shares(self):
        self.share('split', self.settings)
        self.share('edit', self.path(1), self.path(2),
                   '-e', editor("open(path, 'ab').write(b'  bb:\\n    user: bb\\n')"))
        self.assertEqual(join(load([self.path(3), self.path(1)]), Stamp.from_pin('1234')),
                         SETTINGS + b'  bb:\n    user: bb\n')

    def test_edit_drops_invalid_settings(self):
        self.share('split', self.settings)
        before = [p.read_bytes() for p in sorted(self.folder.glob('*.share'))]
        self.share('edit', self.path(1), self.path(2),
                   '-e', editor("open(path, 'w').write('a: [unclosed')"), input='n\n')
        self.assertEqual([p.read_bytes() for p in sorted(self.folder.glob('*.share'))], before)

    def test_service_loads_shares(self):
        self.share('split', self.settings)
        sys.modules.setdefault('pynput', mock.MagicMock())
        sys.modules.setdefault('pyperclip', mock.MagicMock())
        from autokeys import service
        with mock.patch.dict('os.environ', PIN):
            settings = service.load_settings([self.path(3), self.path(2)])
        self.assertEqual(settings['credentials']['aa']['user'], 'aa-user')
        self.assertEqual(service.load_settings([self.settings]), settings)


if __name__ == '__main__':
    unittest.main()
