#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${TWILIO_ACCOUNT_SID:?Set TWILIO_ACCOUNT_SID in .env}"
: "${TWILIO_AUTH_TOKEN:?Set TWILIO_AUTH_TOKEN in .env}"
: "${TWILIO_PHONE_NUMBER:?Set TWILIO_PHONE_NUMBER in .env}"
: "${PUBLIC_WEBHOOK_BASE_URL:?Set PUBLIC_WEBHOOK_BASE_URL in .env}"

STATUS_URL="${PUBLIC_WEBHOOK_BASE_URL%/}/webhooks/twilio/voice/status"
VOICE_URL="${PUBLIC_WEBHOOK_BASE_URL%/}/webhooks/twilio/voice"
API="https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}"

echo "Configuring Twilio voice webhooks for ${TWILIO_PHONE_NUMBER}"
echo "  Voice URL:   ${VOICE_URL}"
echo "  Status URL:  ${STATUS_URL}"

PHONE_SID="$(
  curl -sS -G "${API}/IncomingPhoneNumbers.json" \
    --data-urlencode "PhoneNumber=${TWILIO_PHONE_NUMBER}" \
    -u "${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); nums=d.get('incoming_phone_numbers',[]); print(nums[0]['sid'] if nums else '')"
)"

if [[ -z "${PHONE_SID}" ]]; then
  echo "Could not find Twilio phone number ${TWILIO_PHONE_NUMBER}" >&2
  exit 1
fi

curl -sS -X POST "${API}/IncomingPhoneNumbers/${PHONE_SID}.json" \
  --data-urlencode "VoiceUrl=${VOICE_URL}" \
  --data-urlencode "VoiceMethod=POST" \
  --data-urlencode "StatusCallback=${STATUS_URL}" \
  --data-urlencode "StatusCallbackMethod=POST" \
  -u "${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('Updated:', d.get('phone_number', d))"

echo "Done. Hangup consolidation should fire on completed calls."