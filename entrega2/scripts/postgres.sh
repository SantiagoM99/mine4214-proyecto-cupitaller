#!/usr/bin/env bash
# Postgres local con pgvector para la base vectorial del proyecto.
#
# Usa los mismos datos de conexión que el laboratorio del curso (.env.example):
# usuario, clave y base "mine4214" en 127.0.0.1:5434. El clúster vive en .pgdata/,
# dentro del proyecto, y no se registra como servicio del sistema.
#
#   scripts/postgres.sh iniciar   # crea el clúster la primera vez y lo arranca
#   scripts/postgres.sh detener
#   scripts/postgres.sh estado
#
# Requiere: brew install postgresql@18 pgvector
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
BIN="${PG_BIN:-/opt/homebrew/opt/postgresql@18/bin}"
DATOS="$RAIZ/.pgdata"
PUERTO="${POSTGRES_PORT:-5434}"
USUARIO="${POSTGRES_USER:-mine4214}"
BASE="${POSTGRES_DB:-mine4214}"

crear_cluster() {
  local clave
  clave="$(mktemp)"
  printf '%s' "${POSTGRES_PASSWORD:-mine4214}" > "$clave"
  LC_ALL="en_US.UTF-8" "$BIN/initdb" -D "$DATOS" -U "$USUARIO" --pwfile="$clave" \
    --auth=scram-sha-256 --encoding=UTF8 > /dev/null
  rm -f "$clave"
}

case "${1:-}" in
  iniciar)
    [ -d "$DATOS" ] || crear_cluster
    if ! "$BIN/pg_ctl" -D "$DATOS" status > /dev/null 2>&1; then
      "$BIN/pg_ctl" -D "$DATOS" -l "$DATOS/postgres.log" \
        -o "-p $PUERTO -c listen_addresses=127.0.0.1" -w start > /dev/null
    fi
    PGPASSWORD="${POSTGRES_PASSWORD:-mine4214}" "$BIN/psql" -h 127.0.0.1 -p "$PUERTO" -U "$USUARIO" -d postgres -tAc \
      "SELECT 1 FROM pg_database WHERE datname = '$BASE'" | grep -q 1 \
      || PGPASSWORD="${POSTGRES_PASSWORD:-mine4214}" "$BIN/createdb" -h 127.0.0.1 -p "$PUERTO" -U "$USUARIO" "$BASE"
    echo "Postgres listo en 127.0.0.1:$PUERTO (base $BASE)"
    ;;
  detener)
    "$BIN/pg_ctl" -D "$DATOS" -m fast stop
    ;;
  estado)
    "$BIN/pg_ctl" -D "$DATOS" status
    ;;
  *)
    echo "Uso: $0 iniciar|detener|estado" >&2
    exit 2
    ;;
esac
