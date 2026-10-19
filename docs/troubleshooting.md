# Troubleshooting & Frequently Asked Questions

This guide covers common integration pitfalls, diagnostic procedures, and error resolutions when running ConversionBridge.

---

## 1. Destination Errors & Resolutions

### Meta CAPI Returns HTTP 400 (OAuthException)
- **Symptom**: `Meta API error (400): Invalid OAuth access token` or `Permissions error`.
- **Cause**: The `META_ACCESS_TOKEN` is expired, lacks permissions, or does not belong to the Meta Business Manager that owns `META_PIXEL_ID`.
- **Solution**:
  1. Verify token validity in Meta's [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/).
  2. Confirm the System User has `ads_management` permissions on the Pixel/Dataset.
  3. Ensure `META_PIXEL_ID` matches your actual Pixel/Dataset numeric ID.

### Meta Low Event Match Quality (EMQ) Score
- **Symptom**: Meta Events Manager displays a match score below 6.0/10.
- **Cause**: Events are submitted without sufficient customer matching parameters.
- **Solution**:
  - Always capture and forward first-party cookies: `_fbp` and `_fbc`.
  - Pass customer `email` and `phone` whenever available (e.g. from checkout or lead forms).
  - Pass `client_ip_address` and `client_user_agent` directly from the user's browser request.

### GA4 Events Not Showing in Realtime Reports
- **Symptom**: GA4 returns HTTP 204 or 200, but events do not appear in GA4 Realtime.
- **Cause**: GA4 Measurement Protocol events require `client_id` (extracted from `_ga` cookie). Without a valid `client_id`, events cannot be linked to sessions.
- **Solution**:
  1. Inspect whether `user_data.client_id` is populated in your payload.
  2. Enable `GA4_DEBUG_MODE=true` in `.env` and check **GA4 Admin > DebugView** to inspect real-time validation warnings.

---

## 2. Gateway Status Codes

| Status Code | Meaning | Action Needed |
|:---|:---|:---|
| **200 OK** | Event processed successfully | Inspect `results` array in response to view destination outcomes. |
| **401 Unauthorized** | Missing or invalid API key | Supply valid `X-API-Key` or `Authorization: Bearer <key>` header. |
| **413 Payload Too Large** | Request exceeds 512 KB | Reduce batch size or prune unnecessary custom metadata. |
| **422 Unprocessable Entity** | Schema or validation failure | Review error details (e.g. invalid timestamp, empty event_id). |
| **429 Too Many Requests** | Rate limit exceeded | Respect `Retry-After` header or adjust `RATE_LIMIT_REQUESTS_PER_MINUTE`. |

---

## 3. Interpreting Destination Dispatch Outcomes

Within the `EventResponse.results` array:
- **`sent`**: Successfully accepted by the external platform API.
- **`test_validated`**: Payload validated and transformed without outbound network transmission (`test_mode: true`).
- **`skipped_consent`**: Blocked because user consent for this platform category was denied or missing.
- **`skipped_duplicate`**: Suppressed because an event with the same `event_id` was already dispatched within the deduplication window.
- **`skipped_disabled`**: Platform integration is turned off in configuration (`META_ENABLED=false` or `GA4_ENABLED=false`).
- **`failed`**: Platform rejected the payload or network request timed out.
