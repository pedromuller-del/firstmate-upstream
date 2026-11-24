#!/usr/bin/env bash
# fm-owner-gap.sh - report active registered projects without an open owner record.
#
# Usage: fm-owner-gap.sh
# Activity means at least three backlog items created in the last seven UTC
# dates, including today. An open task with an exact Owner of: <project> body
# line covers that project. Prints one owner-gap line per uncovered project.
set -eu

case "${1:-}" in
  -h|--help) sed -n '2,7s/^# \{0,1\}//p' "$0"; exit 0 ;;
esac
[ "$#" -eq 0 ] || { printf 'Usage: fm-owner-gap.sh\n' >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FM_ROOT="${FM_ROOT_OVERRIDE:-$(cd "$SCRIPT_DIR/.." && pwd)}"
FM_HOME="${FM_HOME:-$FM_ROOT}"
DATA="${FM_DATA_OVERRIDE:-$FM_HOME/data}"
REG="$DATA/projects.md"
[ -e "$REG" ] || exit 0

rows=$(bash "$SCRIPT_DIR/fm-tasks-axi.sh" list --fields created,body) || exit $?
printf '%s\n' "$rows" | perl -MJSON::PP -MPOSIX=strftime -e '
  use warnings;
  use strict;
  binmode STDIN, ":encoding(UTF-8)";
  binmode STDOUT, ":encoding(UTF-8)";
  open my $registry, "<:encoding(UTF-8)", $ARGV[0] or die "$ARGV[0]: $!\n";
  my %projects;
  while (<$registry>) {
    chomp;
    $projects{$1} = 1 if /^- (.+?)(?: \[| - |$)/;
  }
  my $now = time;
  my $today = strftime("%Y-%m-%d", gmtime($now));
  my $cutoff = strftime("%Y-%m-%d", gmtime($now - 6 * 86400));
  my $json = JSON::PP->new->allow_nonref;
  my (%column, %activity, %owner);
  while (<STDIN>) {
    chomp;
    if (/^tasks\[\d+\]\{([^}]*)\}:$/) {
      my @names = split /,/, $1;
      @column{@names} = 0 .. $#names;
      next;
    }
    if (!/^  (.*)$/) {
      %column = ();
      next;
    }
    next unless %column;
    my @fields = map { /^"/ ? $json->decode($_) : $_ }
      $1 =~ /("(?:[^"\\]|\\.)*"|[^,]+)/g;
    my ($state, $repo, $created, $body) = @fields[@column{qw(state repo created body)}];
    if (exists $projects{$repo} && $created =~ /^(\d{4}-\d\d-\d\d)/ && $1 ge $cutoff && $1 le $today) {
      ++$activity{$repo};
    }
    next if $state eq "done";
    for my $line (split /\n/, $body) {
      $owner{$1} = 1 if $line =~ /^Owner of: (.+)$/;
    }
  }
  for my $project (sort keys %activity) {
    print "owner-gap $project\n" if $activity{$project} >= 3 && !$owner{$project};
  }
' "$REG"
