#!/bin/bash
# 兼容壳:安装逻辑在跨平台的 install.py(Windows 请直接 python install.py)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/install.py" "$@"
