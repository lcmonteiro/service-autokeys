#!/usr/bin/env bash
# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
# autokeys launcher
#
#   ./run.sh                     use the default settings file
#   ./run.sh path/to/config.yml  use a specific settings file
#
# The environment is created and kept in sync by uv on every run.
# =======================================================================================
set -euo pipefail

# ---------------------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------------------
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG_DIR="${AUTOKEYS_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/autokeys}"

# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------
die() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<EOF
usage: run.sh [settings-file]

  settings-file  path of the settings file, by default the first of
                 \$AUTOKEYS_CONFIG, $CFG_DIR/config.yml, ./config.yml
EOF
}

# first settings file that exists, from the most specific to the most generic
resolve_settings() {
    local candidate
    for candidate in "${AUTOKEYS_CONFIG:-}" "$CFG_DIR/config.yml" "$SRC_DIR/config.yml"; do
        if [ -n "$candidate" ] && [ -f "$candidate" ]; then
            printf '%s' "$candidate"
            return
        fi
    done
    die "no settings file found, create $CFG_DIR/config.yml (see config-sample.yml)"
}

# ---------------------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------------------
case "${1:-}" in
    -h|--help) usage; exit 0 ;;
esac

command -v uv >/dev/null 2>&1 || {
    [ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
    command -v uv >/dev/null 2>&1 || die "uv not found, run setup.sh first"
}

if [ $# -gt 0 ]; then
    SETTINGS="$1"
    shift
    [ -f "$SETTINGS" ] || die "settings file not found: $SETTINGS"
else
    SETTINGS="$(resolve_settings)"
fi

exec uv run --project "$SRC_DIR" --no-dev autokeys "$SETTINGS" "$@"
# =======================================================================================
# End
# =======================================================================================
