#!/usr/bin/env bash
# Claude quota failover, called under fm-control's exact-task lifecycle lock.
# The journal remembers observed exhausted accounts across replacement launches.
# Reset text is display data, not a timestamp: Claude formats it in the pane's
# timezone. Retain each observation for at most its quota window.

fm_secondmate_quota_screen() {
  fm_composer_strip_ansi | awk '
    { sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, "") }
    /^❯/ { composer = $0 }
    {
      sub(/^⎿[[:space:]]+/, "")
      if ($0 ~ /^You\047ve hit your (weekly |session |daily )?limit · resets [[:alnum:]][[:alnum:] :.,()+\/-]*$/) {
        hint = $0
        sub(/^.* · /, "", hint)
        window = ($0 ~ /weekly/) ? 604800 : (($0 ~ /daily/) ? 86400 : 18000)
      }
    }
    END {
      if (composer == "❯ Usage limit reached") {
        if (!hint) { hint = "reset time not shown"; window = 18000 }
      } else if (composer || !hint) exit 1
      print window "\t" hint
    }'
}

fm_secondmate_quota_next() { # <account-list> <current> <journal> <window> <reset>
  local listed=$1 current=$2 journal=$3 window=$4 reset=$5 tmp now
  [ ! -L "$journal" ] && { [ ! -e "$journal" ] || [ -f "$journal" ]; } || return 1
  now=$(date +%s) || return 1
  tmp=$(mktemp "$journal.XXXXXX") || return 1
  if ! FM_QUOTA_CURRENT="$current" awk -F '\t' -v now="$now" '
    $1 != ENVIRON["FM_QUOTA_CURRENT"] && $2 ~ /^[0-9]+$/ && $2 > now { print }
  ' "$(if [ -f "$journal" ]; then printf '%s' "$journal"; else printf /dev/null; fi)" > "$tmp" \
    || ! printf '%s\t%s\t%s\n' "$current" "$((now + window))" "$reset" >> "$tmp" \
    || ! mv -f -- "$tmp" "$journal"; then
    rm -f -- "$tmp"
    return 1
  fi
  printf '%s\n' "$listed" | FM_QUOTA_CURRENT="$current" awk -F '\t' '
    FILENAME != "-" { exhausted[$1] = 1; next }
    $0 == ENVIRON["FM_QUOTA_CURRENT"] { after = 1; next }
    !($0 in exhausted) {
      if (after) { print; done = 1; exit }
      if (!before) before = $0
    }
    END { if (!done && before) print before }
  ' "$journal" -
}
