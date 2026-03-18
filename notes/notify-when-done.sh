#!/bin/bash
# Watch notes/explainers-for-terms.md; when it stops changing for 30s, show a notification.
# Usage: ./notes/notify-when-done.sh   (run in repo root)
FILE="${1:-notes/explainers-for-terms.md}"
echo "Watching $FILE — you'll get a notification when it hasn't changed for 30 seconds."
last=0
while true; do
  m=$(stat -f %m "$FILE" 2>/dev/null || stat -c %Y "$FILE" 2>/dev/null)
  [ -n "$m" ] && last=$m
  sleep 30
  m=$(stat -f %m "$FILE" 2>/dev/null || stat -c %Y "$FILE" 2>/dev/null)
  if [ -n "$m" ] && [ "$m" -eq "$last" ]; then
    osascript -e 'display notification "Explainers file stable (agent may be done)." with title "SeedPods"'
    echo "Notification sent."
    exit 0
  fi
done
