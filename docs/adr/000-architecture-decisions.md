# ADR 000: Backend & Frontend Frameworks

Date: 2025-12-01
Status: Accepted
Decision: Use FastAPI for backend, Next.js for frontend
Context: Need Python-first backend for AI simulations, serverless deployment, modern frontend for dashboards
Alternatives Considered:
  - Flask: simpler but less async-friendly
  - Django: too heavy for microservices
Consequences:
  - Backend is async-friendly and ML-ready
  - Frontend is easy to deploy serverlessly
  - AI agents can generate code against FastAPI endpoints
