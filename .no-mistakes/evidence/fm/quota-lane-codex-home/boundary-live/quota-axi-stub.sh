#!/usr/bin/env bash
set -eu
[ "$#" -eq 1 ] && [ "$1" = --json ] || exit 2
[ -z "${TYPESAFE_API_KEY+x}" ] && [ -z "${TYPESAFE_API_KEY_PRIVATE+x}" ] || exit 3
printf '%s\n' "$*" >> "$FM_HOME/quota-axi.calls"
cat "$FM_HOME/quota.json"
