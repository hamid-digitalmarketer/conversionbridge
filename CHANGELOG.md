# Changelog

All notable changes to ConversionBridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-19

### Added
- Core FastAPI application with dual Uvicorn & Firebase Cloud Functions v2 runtime support.
- REST API endpoints:
  - `POST /api/v1/events` (Ingestion and cross-channel dispatch)
  - `POST /api/v1/events/test` (Schema validation & safe payload preview)
  - `GET /health` (Operational health check)
  - `GET /api/v1/destinations/status` (Safe platform configuration review)
- Meta Conversions API (CAPI) adapter with automated SHA-256 user data hashing and test event code support.
- Google Analytics 4 (GA4) Measurement Protocol adapter with DebugView validation (`/debug/mp/collect`) and parameter mapping.
- Privacy-first `ConsentEngine` enforcing separate advertising and analytics consent with fail-closed rules.
- Cross-channel `DeduplicationService` with 48-hour deduplication window and destination key isolation.
- Dual storage backends: `MemoryStorage` (local dev/testing) and `FirestoreStorage` (production serverless).
- Security perimeter: API key verification, sliding-window rate limiting (120 req/min), payload size limits (512 KB), and secret redaction.
- Complete automated test suite: 38 unit & integration tests covering validation, consent, deduplication, destinations, and security.
- Comprehensive documentation, architecture diagram, deployment guide, and client integration examples in Python and JavaScript.
