#!/usr/bin/env bash
# Instala el watchdog del enlace con la antena en la RPi5. Correr desde la PC:
#   bash scripts/rpi5/install-link-watchdog.sh [host-ssh]   (default: leonode-rpi)
set -euo pipefail
HOST="${1:-leonode-rpi}"
DIR="$(cd "$(dirname "$0")" && pwd)"

scp -q "$DIR"/starlink-link-watchdog.{sh,service,timer} "$HOST":/tmp/
ssh -t "$HOST" '
sudo install -m 0755 /tmp/starlink-link-watchdog.sh /usr/local/bin/
sudo install -m 0644 /tmp/starlink-link-watchdog.service /tmp/starlink-link-watchdog.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now starlink-link-watchdog.timer
sudo systemctl start starlink-link-watchdog.service
systemctl list-timers starlink-link-watchdog.timer --no-pager | head -2
systemctl show starlink-link-watchdog.service -p Result
'
