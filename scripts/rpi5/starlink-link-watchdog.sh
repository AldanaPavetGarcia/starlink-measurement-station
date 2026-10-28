#!/usr/bin/env bash
# Watchdog del enlace cableado RPi5 <-> antena Starlink.
#
# Incidente 21-28/10/2026: eth0 perdió su IPv4 (NetworkManager pedía DHCP cada
# 5 min y no obtenía lease) y el extractor estuvo 7 días sin llegar a
# 192.168.100.1, sin que se cayera ningún contenedor. Reactivar la conexión lo
# resolvió al instante; este script hace eso mismo cuando la antena no responde.
#
# Lo corre starlink-link-watchdog.timer cada 5 minutos. Loguea en el journal:
#   journalctl -t starlink-link-watchdog
set -u

IFACE="${IFACE:-eth0}"
ANTENNA="${ANTENNA:-192.168.100.1}"
TAG=starlink-link-watchdog

log() { logger -t "$TAG" "$*"; }
antenna_ok() { ping -c 3 -W 2 -I "$IFACE" "$ANTENNA" >/dev/null 2>&1; }

antenna_ok && exit 0

# Sin cable o antena apagada: reactivar la conexión no sirve de nada.
if [ "$(cat "/sys/class/net/$IFACE/carrier" 2>/dev/null)" != "1" ]; then
    log "antena $ANTENNA sin respuesta y $IFACE sin enlace físico (cable/antena), no se reactiva"
    exit 0
fi

CONN="$(nmcli -g GENERAL.CONNECTION device show "$IFACE" 2>/dev/null)"
IPV4="$(ip -4 -o addr show dev "$IFACE" | awk '{print $4}')"
log "antena $ANTENNA sin respuesta por $IFACE (IPv4: ${IPV4:-ninguna}), reactivando '${CONN:-$IFACE}'"

if [ -n "$CONN" ]; then
    nmcli connection down "$CONN" >/dev/null 2>&1
    sleep 3
    nmcli connection up "$CONN" >/dev/null 2>&1
else
    nmcli device connect "$IFACE" >/dev/null 2>&1
fi
sleep 10

if antenna_ok; then
    log "enlace recuperado ($IFACE: $(ip -4 -o addr show dev "$IFACE" | awk '{print $4}'))"
else
    log "la antena sigue sin responder tras reactivar $IFACE, se reintenta en el próximo ciclo"
    exit 1
fi
