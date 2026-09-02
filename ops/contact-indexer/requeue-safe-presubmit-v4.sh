#!/usr/bin/env bash
set -euo pipefail
DB="exior_contact"

# Requeue only statuses that are pre-submit by construction. Do NOT touch any
# status that may have clicked/submitted (FAILED_CONFIRMATION, SUBMIT_ACCEPTED,
# SUCCESS_CONFIRMED).
sudo -u postgres psql -d "$DB" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;

WITH retryable AS (
  SELECT s.company_id
  FROM submissions_v3 s
  WHERE s.status IN ('REQUIRED_PHONE','NO_MESSAGE_FIELD')
), upd AS (
  UPDATE outreach_queue q
  SET status='MESSAGE_READY', updated_at=now()
  FROM retryable r
  WHERE q.company_id=r.company_id
  RETURNING q.company_id
)
DELETE FROM submissions_v3 s
USING retryable r
WHERE s.company_id=r.company_id;

COMMIT;

SELECT status, count(*)
FROM submissions_v3
GROUP BY status
ORDER BY count(*) DESC;

SELECT count(*) AS message_ready
FROM outreach_queue
WHERE status='MESSAGE_READY';
SQL
