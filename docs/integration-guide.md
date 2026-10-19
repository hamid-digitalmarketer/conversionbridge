# First-Party Integration Guide

This guide details best practices for integrating ConversionBridge with popular web platforms, e-commerce engines, and CRM backends.

---

## 1. Integration Patterns

### Pattern A: Backend Post-Checkout Hook (Recommended for E-Commerce)
In e-commerce systems (Shopify, WooCommerce, Magento), browser-based pixel tracking often drops 10%–25% of purchases due to network interruptions, ad blockers, or users closing tabs before order confirmation scripts finish executing.

**Implementation**:
Trigger an HTTP POST from your backend order completion webhook:
```
Shopify / WooCommerce Backend (Webhook)
             |
             v
   ConversionBridge Gateway (POST /api/v1/events)
             |
       +-----+-----+
       |           |
       v           v
    Meta CAPI     GA4 MP
```

### Pattern B: Lead Generation Forms (Webflow, WordPress, Custom Forms)
When a user submits a contact or consultation form:
1. Capture client context in hidden fields:
   - `_fbp` cookie
   - `_fbc` cookie (or `fbclid` query parameter)
   - `_ga` cookie (client ID)
2. Submit form data to your backend API.
3. Backend validates lead submission, saves to database/CRM, and forwards a sanitized `Lead` event to ConversionBridge.

### Pattern C: CRM Offline Revenue Sync (Closed-Won Opportunities)
When a lead converts to paying revenue in your CRM (HubSpot, Salesforce):
1. Retrieve original `lead_id` or `external_id` and original `event_time`.
2. Send an offline `Purchase` or `QualifiedLead` event to ConversionBridge with `action_source="system_generated"`.
3. Meta and GA4 attribute downstream revenue back to the original advertising campaign.

---

## 2. Recommended Conversion Event Names

| Business Goal | Standard Event Name | Meta Standard Equivalent | GA4 Standard Equivalent |
|:---|:---|:---|:---|
| Form Inquiry | `Lead` | `Lead` | `generate_lead` |
| Completed Purchase | `Purchase` | `Purchase` | `purchase` |
| Scheduled Call | `Schedule` | `Schedule` | `book_appointment` |
| Newsletter Sign-Up | `CompleteRegistration` | `CompleteRegistration` | `sign_up` |
| Direct Contact | `Contact` | `Contact` | `contact` |
| Content View | `ViewContent` | `ViewContent` | `view_item` |
