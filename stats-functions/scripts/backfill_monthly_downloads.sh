#!/usr/bin/env bash
#
# Rerun stats-monthly-downloads for every month from START_MONTH through
# END_MONTH (inclusive), so monthly_downloads is recomputed from hourly_downloads
# with the month boundaries of the deployed function
# (stats-functions/monthly_downloads/src/main.py).
#
# Each month is published with attribute "month=YYYY-MM-01", which
# validate_month() reads; the function replaces that month's row in a single
# transaction, so rerunning a month is safe.
#
# Only rerun months that hourly_downloads fully covers: a month recomputed from
# partial hourly data replaces its stored total with a smaller one. Check first:
#   SELECT MIN(start_dttm), MAX(start_dttm) FROM hourly_downloads;
#   SELECT DATE_FORMAT(start_dttm, '%Y-%m') AS m, COUNT(DISTINCT start_dttm) AS hours
#   FROM hourly_downloads GROUP BY m ORDER BY m;
#
# Usage:
#   ./backfill_monthly_downloads.sh [--dry-run] [--yes] [--sleep-seconds N] START_MONTH [END_MONTH]
#
# START_MONTH and END_MONTH are YYYY-MM. END_MONTH defaults to last month; the
# current month is refused, since it isn't over yet.
#
# Env vars (all optional, shown with defaults):
#   PROJECT=arxiv-production
#   TOPIC=stats-monthly-downloads
#   SERVICE_NAME=stats-monthly-downloads
#   SLEEP_SECONDS=60   (also settable via --sleep-seconds)
#
# Examples:
#   ./backfill_monthly_downloads.sh --dry-run 2024-01
#   ./backfill_monthly_downloads.sh --yes 2024-01 2026-09
#   PROJECT=arxiv-development ./backfill_monthly_downloads.sh 2025-06 2025-08

set -euo pipefail

PROJECT="${PROJECT:-arxiv-production}"
TOPIC="${TOPIC:-stats-monthly-downloads}"
SERVICE_NAME="${SERVICE_NAME:-stats-monthly-downloads}"
SLEEP_SECONDS="${SLEEP_SECONDS:-60}"

DRY_RUN=false
ASSUME_YES=false
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --yes|-y) ASSUME_YES=true; shift ;;
    --sleep-seconds=*) SLEEP_SECONDS="${1#*=}"; shift ;;
    --sleep-seconds) SLEEP_SECONDS="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,33p' "$0"
      exit 0
      ;;
    *) POSITIONAL+=("$1"); shift ;;
  esac
done

if [[ "${#POSITIONAL[@]}" -lt 1 ]]; then
  echo "START_MONTH (YYYY-MM) is required. See --help." >&2
  exit 1
fi
START_MONTH="${POSITIONAL[0]}"
END_MONTH="${POSITIONAL[1]:-}"

# list the months (YYYY-MM-01), refusing the current arXiv-local month. Done in
# python rather than `date` since GNU/BSD date flags aren't portable.
MONTHS="$(python3 - "$START_MONTH" "$END_MONTH" <<'PYEOF'
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

def parse(value):
    try:
        return datetime.strptime(value, "%Y-%m").date()
    except ValueError:
        sys.exit(f"expected a month as YYYY-MM, got {value!r}")

now = datetime.now(ZoneInfo("America/New_York"))
current = date(now.year, now.month, 1)
last = date(current.year - (current.month == 1), (current.month - 2) % 12 + 1, 1)

start = parse(sys.argv[1])
end = parse(sys.argv[2]) if sys.argv[2] else last

if end >= current:
    sys.exit(f"{end:%Y-%m} isn't over yet in arXiv local time; the latest month allowed is {last:%Y-%m}")
if start > end:
    sys.exit(f"START_MONTH {start:%Y-%m} is after END_MONTH {end:%Y-%m}")

month = start
while month <= end:
    print(month.isoformat())
    month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
PYEOF
)"
MONTH_COUNT="$(printf '%s\n' "$MONTHS" | grep -c .)"

echo "Project:       $PROJECT"
echo "Topic:         $TOPIC"
echo "Months:        $(printf '%s\n' "$MONTHS" | head -1) through $(printf '%s\n' "$MONTHS" | tail -1) ($MONTH_COUNT)"
echo "Sleep between: ${SLEEP_SECONDS}s"
echo "Dry run:       $DRY_RUN"
echo
printf '  %s\n' $MONTHS
echo

DAY_UTC="$(date -u +%d)"
if [[ "$DAY_UTC" == "01" || "$DAY_UTC" == "02" || "$DAY_UTC" == "03" ]]; then
  echo "Warning: the scheduled job also runs on the 1st-3rd of the month; avoid overlapping it."
  echo
fi

ESTIMATED_MINUTES=$(( (MONTH_COUNT - 1 > 0 ? MONTH_COUNT - 1 : 0) * SLEEP_SECONDS / 60 ))
echo "This will take roughly ${ESTIMATED_MINUTES} minutes to run (waits ${SLEEP_SECONDS}s between each publish)."

if [[ "$DRY_RUN" == true ]]; then
  echo
  echo "Dry run - not publishing anything."
  exit 0
fi

# safety gate before rewriting production data
if [[ "$ASSUME_YES" != true ]]; then
  read -r -p "Proceed and publish $MONTH_COUNT message(s) to '$TOPIC' in project '$PROJECT'? [y/N] " CONFIRM
  if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
  fi
fi

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# publish one month at a time; sleeping between each keeps the DB from running
# overlapping month-long sums
INDEX=0
for MONTH in $MONTHS; do
  INDEX=$((INDEX + 1))
  echo "[$INDEX/$MONTH_COUNT] $(date -u +%Y-%m-%dT%H:%M:%SZ) publishing month=$MONTH"
  gcloud pubsub topics publish "$TOPIC" \
    --project="$PROJECT" \
    --message="" \
    --attribute="month=$MONTH"

  if [[ "$INDEX" -lt "$MONTH_COUNT" ]]; then
    echo "  sleeping ${SLEEP_SECONDS}s before next publish..."
    sleep "$SLEEP_SECONDS"
  fi
done

LOG_FILTER="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND (textPayload=~\"Downloads for month|NoRetry\" OR jsonPayload.message=~\"Downloads for month|NoRetry\") AND timestamp>=\"${STARTED_AT}\""

echo
echo "Done. Published $MONTH_COUNT message(s)."
echo "In a few minutes, check that each month logged its new total (and nothing failed):"
echo "  gcloud logging read '${LOG_FILTER}' --project=$PROJECT --order=asc --format='value(timestamp,textPayload,jsonPayload.message)'"
