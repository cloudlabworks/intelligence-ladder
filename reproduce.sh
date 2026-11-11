#!/usr/bin/env bash
# Verify package hashes with the system tool, then run the full Python check.
set -euo pipefail
cd "$(dirname "$0")"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum --quiet -c SHA256SUMS
else
  shasum -a 256 --quiet -c SHA256SUMS
fi
echo "SHA256SUMS: system checksum tool OK"
exec python3 reproduce.py "$@"
