#!/bin/bash
# 兼容壳:卸载逻辑在跨平台的 uninstall.py(Windows 请直接 python uninstall.py)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/uninstall.py" "$@"
