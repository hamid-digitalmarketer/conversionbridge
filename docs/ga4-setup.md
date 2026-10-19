# Google Analytics 4 (GA4) Measurement Protocol Guide

This guide explains how to configure and deploy server-to-server tracking for Google Analytics 4 with ConversionBridge.

---

## 1. Prerequisites in Google Analytics 4

To send events via the Measurement Protocol:
1. A **GA4 Measurement ID** (e.g. `G-XXXXXXXXXX`).
2. A **Measurement Protocol API Secret**.

### Creating an API Secret in GA4
1. Navigate to **Google Analytics** > **Admin** (gear icon).
2. Under **Data collection and modification**, click **Data Streams**.
3. Select your active Web Data Stream.
4. Scroll down to **Measurement Protocol API secrets**.
5. Click **Create** > enter a nickname (e.g. `ConversionBridge Server`).
6. Copy the **Secret Value**.

---

## 2. Configuration Settings

Configure your environment variables:

```ini
GA4_ENABLED=true
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
GA4_API_SECRET=your_measurement_protocol_api_secret_here
# Set to true during development to inspect validation hints
GA4_DEBUG_MODE=false
```

---

## 3. Client Identifier Requirements

The GA4 Measurement Protocol requires a persistent identifier to associate events with a user session:
- **`client_id` (Required)**: Represents an anonymous browser/device instance. Usually extracted from the `_ga` cookie on your website:
  ```javascript
  // Extract client_id from _ga cookie (e.g. GA1.1.123456789.1729304859)
  const gaCookie = document.cookie.split('; ').find(row => row.startsWith('_ga='));
  const clientId = gaCookie ? gaCookie.split('.').slice(-2).join('.') : null;
  ```
- **`user_id` (Optional)**: A first-party known customer ID (e.g. CRM user ID or logged-in account ID). Enables cross-device user journey tracking.

---

## 4. Debugging with GA4 DebugView

Because GA4's production endpoint (`/mp/collect`) returns `HTTP 204 No Content` for all structurally valid HTTP requests (without validating event syntax or parameter names), debugging can be challenging.

ConversionBridge provides native support for GA4's validation endpoint:
1. Set `GA4_DEBUG_MODE=true` in `.env`.
2. All outbound events will be routed to `https://www.google-analytics.com/debug/mp/collect`.
3. ConversionBridge parses the returned `validationMessages` array and logs detailed field warnings.
4. Events will simultaneously appear inside the **GA4 Admin > DebugView** console.

---

## 5. Reporting Expectations & Attribution Nuance

> [!NOTE]
> Receiving an HTTP 204 or 200 from the GA4 Measurement Protocol indicates that Google received the payload. It does **not** guarantee immediate appearance in standard attribution reports.
> - **DebugView**: Appears within seconds.
> - **Realtime Reports**: Appears within 5 to 15 minutes.
> - **Standard Attribution Reports**: Typically requires 24 to 48 hours for data processing and machine learning attribution modeling.
