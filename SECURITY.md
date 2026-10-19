# Security Policy

ConversionBridge takes security and privacy seriously.

---

## Reporting a Vulnerability

If you discover a potential security vulnerability or secret leakage issue within this project, please report it privately:

- **Direct Inquiries**: Contact Muhammad Hamid via WhatsApp: [`+92 316 7417135`](https://wa.me/923167417135)
- **Do not** create public GitHub issues for security vulnerabilities or exploit demonstrations.

We aim to acknowledge reports within 24 hours and coordinate a timely fix and advisory.

---

## Security Practices
- ConversionBridge enforces one-way SHA-256 hashing for direct customer identifiers.
- Production deployments must run exclusively over HTTPS.
- Never commit `.env` files or API secrets into version control.
- Use Google Cloud Secret Manager for production API keys and access tokens.
