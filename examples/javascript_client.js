/**
 * ConversionBridge JavaScript Client Example
 *
 * Demonstrates submitting consent-aware conversion events from a web application
 * or Node.js service to ConversionBridge.
 *
 * IMPORTANT SECURITY NOTE:
 * Never embed your Meta Access Token or GA4 API Secret in frontend JavaScript.
 * ConversionBridge acts as your secure server-side gateway: frontend clients only
 * post to your ConversionBridge API endpoint.
 */

const CONVERSIONBRIDGE_ENDPOINT = "https://your-project.cloudfunctions.net/conversionbridge_api/api/v1/events";

/**
 * Helper to retrieve first-party cookie values (e.g. _fbp, _ga)
 */
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

/**
 * Track a Lead conversion after successful form submission
 * @param {Object} formData Customer form inputs
 * @param {Object} consentState CMP consent state (e.g. from OneTrust, Cookiebot)
 */
async function trackLeadConversion(formData, consentState) {
  // Extract first-party context
  const fbp = getCookie('_fbp');
  const fbc = getCookie('_fbc');
  const gaCookie = getCookie('_ga');
  // GA4 client_id is typically the last two numeric parts of the _ga cookie (e.g. GA1.1.123456789.1234567890)
  const clientId = gaCookie ? gaCookie.split('.').slice(-2).join('.') : null;

  const eventPayload = {
    event_name: "Lead",
    event_id: `lead_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
    event_time: Math.floor(Date.now() / 1000),
    event_source_url: window.location.href,
    action_source: "website",
    consent: {
      analytics: Boolean(consentState.analytics),
      advertising: Boolean(consentState.advertising),
      granted_at: Math.floor(Date.now() / 1000)
    },
    user_data: {
      email: formData.email || null,
      phone: formData.phone || null,
      first_name: formData.firstName || null,
      last_name: formData.lastName || null,
      client_id: clientId,
      fbp: fbp,
      fbc: fbc
    },
    custom_data: {
      content_name: formData.serviceRequested || "General Inquiry",
      content_category: "Lead Generation",
      value: formData.estimatedBudget || 0.00,
      currency: "USD"
    },
    destinations: ["meta", "ga4"],
    test_mode: false
  };

  try {
    const response = await fetch(CONVERSIONBRIDGE_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Include API key if REQUIRE_API_KEY is enabled
        // "X-API-Key": "YOUR_FIRST_PARTY_CLIENT_KEY"
      },
      body: JSON.stringify(eventPayload)
    });

    const result = await response.json();
    console.log("ConversionBridge response:", result);
    return result;
  } catch (error) {
    console.error("Failed to transmit conversion event to ConversionBridge:", error);
    return null;
  }
}

// Example usage:
if (typeof module !== "undefined" && module.exports) {
  module.exports = { trackLeadConversion };
}
