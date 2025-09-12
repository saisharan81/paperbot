#!/usr/bin/env bash
set -euo pipefail

PORT=${PROMETHEUS_PORT:-8000}
URL="http://localhost:${PORT}/metrics"

echo "[smoke] Checking Paperbot metrics at ${URL}"

# Try to curl a few times in case the app is starting up
tries=0
until curl -fsS "$URL" >/tmp/metrics.$$ 2>/dev/null || [[ $tries -ge 10 ]]; do
  tries=$((tries+1))
  sleep 1
done

if [[ ! -s /tmp/metrics.$$ ]]; then
  echo "[smoke] Could not fetch metrics. Is the app running?"
  echo "Hint: ENABLE_PATTERN_OBS_DEMO=1 docker compose up --build"
  exit 1
fi

ok=0
grep -q '^pattern_detected_total' /tmp/metrics.$$ && ok=$((ok+1))
grep -q '^pattern_intent_total' /tmp/metrics.$$ && ok=$((ok+1))
grep -q '^pattern_to_intent_latency_seconds_bucket' /tmp/metrics.$$ && ok=$((ok+1))

rm -f /tmp/metrics.$$

if [[ $ok -lt 3 ]]; then
  echo "[smoke] Missing expected pattern metrics. Ensure ENABLE_PATTERN_OBS_DEMO=1 and wait one interval."
  echo "Check: curl -s ${URL} | egrep 'pattern_detected_total|pattern_intent_total|pattern_to_intent_latency_seconds_bucket'"
  exit 2
fi

echo "[smoke] OK: pattern metrics present."
