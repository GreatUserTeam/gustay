#!/bin/sh
# Refresh the freedesktop databases after a .deb installation so the
# application/x-gustay MIME type and the .gustay association appear at once.
set -e

if command -v update-mime-database >/dev/null 2>&1; then
  update-mime-database /usr/share/mime || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi

exit 0
