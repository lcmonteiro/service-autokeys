# service-autokeys

Keyboard driven service that types your credentials and runs commands from hotkeys.

It listens to the keyboard and reacts to key patterns: a hotkey combination followed
by a sequence of keys. The project is managed with [uv](https://docs.astral.sh/uv/).

## Install

One line, no prerequisites other than `wget` (or `curl`) and `git`:

```bash
wget -qO- https://raw.githubusercontent.com/lcmonteiro/service-autokeys/main/setup.sh | bash
```

```bash
curl -fsSL https://raw.githubusercontent.com/lcmonteiro/service-autokeys/main/setup.sh | bash
```

The installer takes care of everything:

1. installs `uv` when it is missing,
2. clones the sources to `~/.local/share/autokeys`,
3. builds the environment from `uv.lock` (uv also fetches the pinned Python),
4. installs the `autokeys` command in `~/.local/bin`,
5. creates `~/.config/autokeys/config.yml` from the sample, readable only by you.

From a checkout the very same script installs from the local sources:

```bash
git clone https://github.com/lcmonteiro/service-autokeys
cd service-autokeys
./setup.sh
```

### Options

| option | description |
| --- | --- |
| `--ref <git-ref>` | branch, tag or commit to install (default `main`) |
| `--dir <path>` | where the sources are cloned (default `~/.local/share/autokeys`) |
| `--config-dir <path>` | where the settings live (default `~/.config/autokeys`) |
| `--no-tool` | build the environment only, do not install the command |

The same values can be set with `AUTOKEYS_REPO`, `AUTOKEYS_REF`, `AUTOKEYS_HOME` and
`AUTOKEYS_CONFIG_DIR`. When piping to `bash`, pass the options after `-s`:

```bash
wget -qO- https://raw.githubusercontent.com/lcmonteiro/service-autokeys/main/setup.sh | bash -s -- --no-tool
```

## Run

```bash
./run.sh                     # uses the first settings file found
./run.sh path/to/config.yml  # uses a specific settings file
```

`run.sh` keeps the environment in sync with `uv` before starting, so it is also the
way to run the service from a development checkout. Without arguments it looks for
`$AUTOKEYS_CONFIG`, then `~/.config/autokeys/config.yml`, then `./config.yml`.

Once `~/.local/bin` is on your `PATH` the installed command does the same:

```bash
autokeys ~/.config/autokeys/config.yml
```

## Settings

```yaml
credentials:
  aa:
    user: aa-user
    pass: aa-pass
    sites: []
  bb:
    user: bb-user
    pass: bb-pass
    sites: []
```

Each entry is reachable by typing its key after a hotkey combination:

| keys | action |
| --- | --- |
| `ctrl`+`alt`+`u` then `aa` | types the user of the `aa` entry |
| `ctrl`+`alt`+`p` then `aa` | types the password of the `aa` entry and stages it in the clipboard |
| `ctrl`+`alt`+`cmd` then `exit` | stops the service |

The file holds passwords in clear text: keep it private (`chmod 600`).

## Development

```bash
uv sync                     # environment with the dev dependencies
uv run autokeys config.yml  # run from the sources
uv run ruff check .         # lint
uv lock --upgrade           # refresh the lock file
uv add <package>            # add a dependency
```

The Python version is pinned in `.python-version` and uv installs it on demand, so
no system Python or virtualenv handling is needed.

## Requirements

`pynput` drives the keyboard through the display server, so a graphical session is
required. On Linux the `evdev` backend is compiled at install time and needs a C
compiler plus the Python headers (`build-essential` and `python3-dev` on Debian and
Ubuntu).
