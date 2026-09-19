#!/usr/bin/env bash
# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
# autokeys installer
#
#   local  : ./setup.sh
#   remote : wget -qO- https://raw.githubusercontent.com/lcmonteiro/service-autokeys/main/setup.sh | bash
#            curl -fsSL https://raw.githubusercontent.com/lcmonteiro/service-autokeys/main/setup.sh | bash
#
# When piped the sources are cloned to $AUTOKEYS_HOME, otherwise the checkout holding
# this script is used. Either way the environment is built with uv.
# =======================================================================================
set -euo pipefail

# ---------------------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------------------
REPO_URL="${AUTOKEYS_REPO:-https://github.com/lcmonteiro/service-autokeys}"
REPO_REF="${AUTOKEYS_REF:-main}"
SRC_DIR="${AUTOKEYS_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/autokeys}"
CFG_DIR="${AUTOKEYS_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/autokeys}"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
INSTALL_TOOL=1

# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------
log()  { printf '\033[1;34m::\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }
has()  { command -v "$1" >/dev/null 2>&1; }

usage() {
    cat <<EOF
usage: setup.sh [options]

  --ref <git-ref>     branch, tag or commit to install (default: ${REPO_REF})
  --dir <path>        where the sources live when cloned (default: ${SRC_DIR})
  --config-dir <path> where the settings file lives (default: ${CFG_DIR})
  --no-tool           only build the project environment, do not install the
                      'autokeys' command on the PATH
  -h, --help          show this help

environment: AUTOKEYS_REPO, AUTOKEYS_REF, AUTOKEYS_HOME, AUTOKEYS_CONFIG_DIR
EOF
}

# fetch a url to stdout with whatever client is available
fetch() {
    if has curl; then curl -fsSL "$1"
    elif has wget; then wget -qO- "$1"
    else die "neither curl nor wget is available"
    fi
}

# ---------------------------------------------------------------------------------------
# arguments
# ---------------------------------------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --ref)        REPO_REF="${2:?--ref needs a value}"; shift 2 ;;
        --dir)        SRC_DIR="${2:?--dir needs a value}"; shift 2 ;;
        --config-dir) CFG_DIR="${2:?--config-dir needs a value}"; shift 2 ;;
        --no-tool)    INSTALL_TOOL=0; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)            usage >&2; die "unknown option: $1" ;;
    esac
done

# ---------------------------------------------------------------------------------------
# uv
# ---------------------------------------------------------------------------------------
ensure_uv() {
    if has uv; then
        log "uv found ($(uv --version))"
        return
    fi
    log "installing uv"
    fetch "https://astral.sh/uv/install.sh" | sh
    # the installer drops uv in the local bin folder, make it visible right away
    [ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
    export PATH="$BIN_DIR:$HOME/.local/bin:$PATH"
    has uv || die "uv installation failed, add $BIN_DIR to your PATH and retry"
    log "uv installed ($(uv --version))"
}

# ---------------------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------------------
# when executed from a checkout use it, otherwise (piped to bash) clone the repository
resolve_sources() {
    local self="${BASH_SOURCE[0]:-}" here
    if [ -n "$self" ] && [ -f "$self" ]; then
        here="$(cd "$(dirname "$self")" && pwd)"
        if [ -f "$here/pyproject.toml" ]; then
            SRC_DIR="$here"
            log "using local sources: $SRC_DIR"
            return
        fi
    fi
    download_sources
}

download_sources() {
    if has git; then
        if [ -d "$SRC_DIR/.git" ]; then
            log "updating sources: $SRC_DIR ($REPO_REF)"
            git -C "$SRC_DIR" fetch --depth 1 origin "$REPO_REF"
            git -C "$SRC_DIR" checkout --quiet --detach FETCH_HEAD
        else
            log "cloning sources: $SRC_DIR ($REPO_REF)"
            rm -rf "$SRC_DIR"
            mkdir -p "$(dirname "$SRC_DIR")"
            git clone --quiet --depth 1 --branch "$REPO_REF" "$REPO_URL" "$SRC_DIR"
        fi
    else
        # no git, fall back to the source tarball
        has tar || die "git or tar is required to download the sources"
        log "downloading sources: $SRC_DIR ($REPO_REF)"
        rm -rf "$SRC_DIR"
        mkdir -p "$SRC_DIR"
        fetch "${REPO_URL%.git}/archive/${REPO_REF}.tar.gz" \
            | tar -xz -C "$SRC_DIR" --strip-components 1
    fi
    [ -f "$SRC_DIR/pyproject.toml" ] || die "no pyproject.toml found in $SRC_DIR"
}

# ---------------------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------------------
check_platform() {
    # pynput talks to the display server, and on linux its evdev backend is compiled
    case "$(uname -s)" in
        Linux)
            has cc || has gcc || warn "no C compiler found: installing 'evdev' may fail, \
install build-essential and python3-dev (or the equivalent for your distribution)"
            ;;
    esac
}

build_environment() {
    log "building the environment with uv"
    if [ -f "$SRC_DIR/uv.lock" ]; then
        uv sync --project "$SRC_DIR" --frozen --no-dev
    else
        uv sync --project "$SRC_DIR" --no-dev
    fi
}

install_command() {
    [ "$INSTALL_TOOL" -eq 1 ] || return 0
    log "installing the 'autokeys' command"
    uv tool install --force --from "$SRC_DIR" autokeys
}

install_settings() {
    local target="$CFG_DIR/config.yml"
    if [ -f "$target" ]; then
        log "settings kept: $target"
        return
    fi
    [ -f "$SRC_DIR/config-sample.yml" ] || return 0
    log "creating settings from sample: $target"
    mkdir -p "$CFG_DIR"
    chmod 700 "$CFG_DIR"
    cp "$SRC_DIR/config-sample.yml" "$target"
    # the settings hold credentials, keep them private
    chmod 600 "$target"
}

# ---------------------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------------------
main() {
    check_platform
    ensure_uv
    resolve_sources
    build_environment
    install_command
    install_settings

    cat <<EOF

  autokeys is installed

    sources  : $SRC_DIR
    settings : $CFG_DIR/config.yml

  edit the settings and start the service with

    $SRC_DIR/run.sh
EOF
    if [ "$INSTALL_TOOL" -eq 1 ]; then
        cat <<EOF

  or, once $BIN_DIR is on your PATH

    autokeys $CFG_DIR/config.yml
EOF
    fi
    echo
}

main
# =======================================================================================
# End
# =======================================================================================
