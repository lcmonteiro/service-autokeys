# autokeys

Type credentials and text snippets from a global hotkey.

Press a chord, type a short trigger, and autokeys swallows the trigger and types
the real thing in its place — into any window, without a browser extension.

```
Ctrl+Alt+U   then  gh   ->  octocat
Ctrl+Alt+P   then  gh   ->  ••••••••
Ctrl+Alt+Cmd then  addr ->  221B Baker Street, London
Ctrl+Alt+Cmd then  exit ->  stops the service
```

## Install

```sh
pip install .
```

Requires Python 3.8+ and a graphical session. On Linux that means X11 — pynput's
`uinput` fallback cannot report whether a key event was injected, which autokeys
relies on to ignore its own typing.

## Configure

Settings live in a YAML file you pass on the command line. **It holds
credentials**, so autokeys refuses to start unless it is private:

```sh
cp config-sample.yml ~/.config/autokeys.yml
chmod 600 ~/.config/autokeys.yml
autokeys ~/.config/autokeys.yml
```

Without a settings file, only the built-in commands are active.

```yaml
options:
  # Also leave the password on the clipboard after typing it, so it can be
  # pasted a second time. Off by default: the clipboard is readable by every
  # process on the machine.
  clipboard: false
  clipboard-timeout: 20

credentials:
  gh:
    user: octocat
    pass-env: GITHUB_PASSWORD   # read from the environment, not from this file
  local:
    user: admin
    pass: hunter2

commands:
  addr: 221B Baker Street, London
```

Each key under `credentials` is the trigger you type after the chord. Triggers
are matched case-insensitively.

### Keeping passwords out of the file

`pass-env: NAME` reads the password from the environment instead of storing it
in the file, which keeps it out of backups and out of version control. Combine
it with whatever you already use to hold secrets:

```sh
GITHUB_PASSWORD="$(pass show github)" autokeys ~/.config/autokeys.yml
```

## Security

autokeys is a keyboard automation tool holding real credentials. What it does
and does not promise:

- The settings file must not be readable by group or others; autokeys checks
  this on startup and refuses to run otherwise. `*.yml` is git-ignored.
- Passwords in the settings file are stored **in plain text**. `pass-env` avoids
  that; prefer it.
- Passwords live in the process's memory while it runs, and are typed as
  synthetic key events — anything that can read your keyboard can read them.
- Clipboard staging is off by default. When enabled, the password is readable by
  every process on the machine until the deadline expires, and is withdrawn only
  if nothing else has claimed the clipboard in the meantime.
- Nothing is logged at any verbosity that contains a username or a password.

## Development

```sh
pip install -e '.[dev]'
pytest
```

The suite runs headless against pynput's `dummy` backend, which folds every
modifier onto a single key. The end-to-end tests in `tests/test_integration.py`
need real, distinct modifiers and skip unless you supply them:

```sh
PYNPUT_BACKEND=xorg xvfb-run -a pytest
```

## How it works

Patterns form a tree. The root holds chords; matching one descends into its
branch, where a sequence selects a leaf, and leaves are actions.

```
{Ctrl+Alt+U}  ->  {gh: type "octocat", local: type "admin"}
{Ctrl+Alt+P}  ->  {gh: type ••••••••, local: type ••••••}
{Ctrl+Alt+Cmd}->  {addr: type "221B…", exit: stop}
```

Each pattern reports `PENDING`, `MATCHED` or `FAILED` as keys arrive. A chord
commits only once all of its keys are back up, so the sequence behind it is read
without the modifiers still masking it. Anything the engine types itself comes
back as an injected event and is discarded — otherwise a password would be fed
straight back into the matcher.

## License

MIT — see [LICENSE](LICENSE).
