#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
environment_file=${DOCKER_ENV:-.env.docker}

usage() {
    echo "Usage: scripts/db.sh backup [backup-file]"
    echo "       scripts/db.sh restore <backup-file>"
    echo "       scripts/db.sh restore-latest"
}

fail() {
    echo "Error: $*" >&2
    exit 1
}

case "$environment_file" in
    .env.docker|.env.docker.*) ;;
    *) fail "Database backups and restores are restricted to Docker development environments." ;;
esac

[ -f "$project_dir/$environment_file" ] || fail "Environment file not found: $environment_file"

cd "$project_dir"

compose() {
    DJANGO_ENV_FILE="$environment_file" docker compose --env-file "$environment_file" "$@"
}

wait_for_database() {
    attempts=0
    until compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; do
        attempts=$((attempts + 1))
        [ "$attempts" -lt 30 ] || fail "Database did not become ready."
        sleep 1
    done
}

backup() {
    backup_file=${1:-"backups/city-guide-$(date -u +%Y%m%dT%H%M%SZ).dump"}

    case "$backup_file" in
        /*) ;;
        *) backup_file="$project_dir/$backup_file" ;;
    esac

    [ ! -e "$backup_file" ] || fail "Backup already exists: $backup_file"
    mkdir -p "$(dirname -- "$backup_file")"

    compose up -d db
    wait_for_database

    if ! compose exec -T db sh -c 'pg_dump --format=custom --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$backup_file"; then
        rm -f "$backup_file"
        fail "Backup failed."
    fi

    echo "Backup created: $backup_file"
}

restore() {
    backup_file=${1:-}
    [ -n "$backup_file" ] || fail "Provide the backup to restore."
    [ -f "$backup_file" ] || fail "Backup not found: $backup_file"
    [ "${CONFIRM_RESTORE:-}" = "yes" ] || fail "Restoring replaces local database data. Re-run with CONFIRM_RESTORE=yes."

    compose up -d db
    wait_for_database
    compose stop web worker >/dev/null

    if ! compose exec -T db sh -c 'pg_restore --clean --if-exists --exit-on-error --single-transaction --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$backup_file"; then
        compose up -d web worker >/dev/null
        fail "Restore failed."
    fi

    compose up -d web worker >/dev/null
    echo "Restore completed: $backup_file"
}

restore_latest() {
    set -- "$project_dir"/backups/*.dump
    [ -e "$1" ] || fail "No backups found in backups/."

    latest_backup=$(ls -t "$project_dir"/backups/*.dump | head -n 1)
    echo "Restoring latest backup: $latest_backup"
    restore "$latest_backup"
}

case "${1:-}" in
    backup)
        shift
        backup "$@"
        ;;
    restore)
        shift
        restore "$@"
        ;;
    restore-latest)
        shift
        [ "$#" -eq 0 ] || fail "restore-latest does not take a backup filename."
        restore_latest
        ;;
    *)
        usage >&2
        exit 1
        ;;
esac
