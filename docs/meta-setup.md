# Meta Conversions API (CAPI) Integration Guide

This guide walks through configuring, testing, and optimizing server-side conversion tracking for Meta Ads using ConversionBridge.

---

## 1. Prerequisites in Meta Business Manager

To send server-side events to Meta, you need:
1. A **Meta Pixel ID** or **Dataset ID** (from Meta Events Manager).
2. A **System User Access Token** with `ads_management` or event-publishing permissions.

### Generating a System User Access Token
1. Open [Meta Business Suite](https://business.facebook.com/) > **Business Settings**.
2. Under **Users**, select **System Users**.
3. Create an Admin or Employee System User (e.g. `ConversionBridge Service`).
4. Click **Generate New Token**.
5. Select your Pixel or Dataset asset and grant `Full Control`.
6. Enable the `ads_management` and `business_management` scopes.
7. Copy the token immediately and store it securely (e.g. in `.env` or Firebase Secret Manager).

---

## 2. Configuration Settings

Add the following values to your `.env` or Firebase Secret Manager:

```ini
META_ENABLED=true
META_PIXEL_ID=123456789012345
META_ACCESS_TOKEN=EAAG_your_generated_system_user_access_token
META_API_VERSION=v20.0
# Optional: Only use in staging/development
META_TEST_EVENT_CODE=TEST12345
```

---

## 3. Data Normalization & Hashing Standards

Meta requires specific normalization before computing SHA-256 digests. ConversionBridge performs these transformations automatically:

| Field | Inbound Format | Normalization Applied | Output Format |
|:---|:---|:---|:---|
| **Email (`em`)** | `Jane.Doe@Example.COM` | Trimmed, lowercased | `[sha256("jane.doe@example.com")]` |
| **Phone (`ph`)** | `+1 (555) 123-4567` | Stripped non-digits | `[sha256("15551234567")]` |
| **Names (`fn`, `ln`)** | ` Jane `, ` Doe ` | Trimmed, lowercased | `[sha256("jane")]`, `[sha256("doe")]` |
| **City (`ct`)** | ` San Francisco ` | Trimmed, lowercased, spaces removed | `[sha256("sanfrancisco")]` |
| **IP Address** | `192.168.1.1` | Preserved as raw string | `"192.168.1.1"` (Unhashed) |
| **User-Agent** | `Mozilla/5.0...` | Preserved as raw string | `"Mozilla/5.0..."` (Unhashed) |
| **`_fbp` / `_fbc`** | `fb.1.1234...` | Preserved as raw string | `"fb.1.1234..."` (Unhashed) |

> [!IMPORTANT]
> Do not hash `client_ip_address`, `client_user_agent`, `fbp`, or `fbc`. Meta expects these parameters in plaintext. ConversionBridge automatically applies the correct rules.

---

## 4. Browser & Server Deduplication

When sending events from both the browser (Meta Pixel) and the server (ConversionBridge):
1. **Event ID**: Both events must share the exact same `event_id` (e.g. `lead_10482_order_901`).
2. **Event Name**: Both events must share the exact same `event_name` (e.g. `Lead` or `Purchase`).

Meta's deduplication engine automatically merges events sharing the same `event_id` and `event_name` received within a 48-hour window, preserving the richer server payload while preventing inflated conversion counts.

---

## 5. Verifying Events in Events Manager

1. Open **Meta Events Manager** > **Data Sources** > Select your Pixel.
2. Click the **Test Events** tab.
3. Copy your unique **Test Code** (e.g. `TEST84920`).
4. Set `META_TEST_EVENT_CODE=TEST84920` in your environment.
5. Submit a conversion event via `POST /api/v1/events`.
6. Watch the event appear in real time inside Meta Events Manager with an `Event Quality Score (EQS)` breakdown.
