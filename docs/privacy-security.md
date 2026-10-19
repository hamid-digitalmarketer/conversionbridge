# Privacy, Consent & Data Security Policy

ConversionBridge is engineered with a strict **privacy-first and fail-closed** security posture. This document outlines how data is protected, how consent is enforced, and how to maintain compliance with global privacy regulations (GDPR, CCPA/CPRA, ePrivacy).

---

## 1. Consent Enforcement & Fail-Closed Behavior

Server-side tracking is **not** a loophole to circumvent browser privacy controls or ad blockers. Applicable laws (including GDPR and CCPA) require lawful basis and consent for collecting and sharing customer data regardless of whether events originate in the browser or on the server.

### Fail-Closed Implementation
- If `DEFAULT_CONSENT_FAIL_CLOSED=true` (default), ConversionBridge requires an explicit `True` boolean signal for the specific destination category:
  - **`consent.advertising = true`**: Required for Meta Conversions API.
  - **`consent.analytics = true`**: Required for GA4 Measurement Protocol.
- If consent is missing, false, or unspecified, the event is immediately blocked with status `skipped_consent`.
- ConversionBridge will **never** synthesize consent or transmit unauthorized data.

---

## 2. Cryptographic Normalization & Hashing

To protect personally identifiable information (PII):
1. **One-Way SHA-256**: All direct identifiers (email, phone, first name, last name, address) are transformed into irreversible 256-bit cryptographic digests before leaving the server.
2. **Standard Normalization**:
   - Emails are lowercased and stripped of leading/trailing whitespace.
   - Phones are stripped of non-digit symbols and prefixed with country codes.
3. **No Double Hashing**: Pre-hashed 64-character hex strings provided by upstream systems are recognized and preserved without redundant hashing.

---

## 3. Data Minimization & Retention

- **Ephemeral Deduplication Only**: ConversionBridge stores only the minimal event key (`destination:event_name:event_id`) and an expiration timestamp. It does **not** persist raw customer names, emails, credit card data, or browsing histories.
- **Automated TTL**: Firestore records automatically expire and are purged after the deduplication window (default 48 hours).
- **Log Sanitization**: All application logs and diagnostic responses automatically redact access tokens, API secrets, authorization headers, and customer identifiers.

---

## 4. Platform Security Defenses

- **Rate Limiting**: Sliding-window throttling restricts volumetric abuse.
- **Payload Clamping**: Maximum request body size of 512 KB prevents memory exhaustion.
- **Input Sanitization**: Rejects payloads containing script injection characters (`<`, `>`, control characters).
- **Trusted Outbound Endpoints**: Destination adapters connect exclusively to hardcoded, verified platform endpoints (`graph.facebook.com` and `google-analytics.com`), preventing Server-Side Request Forgery (SSRF).
