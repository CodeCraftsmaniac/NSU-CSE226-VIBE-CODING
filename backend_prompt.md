# Backend Audit + Auto-Fix Prompt (Use With Top AI Models)

You are a senior principal backend engineer and security reviewer.
Your mission is to perform a full, production-grade backend audit for this repository, fix all issues you can safely fix, and leave the backend in a deploy-ready state.

## Primary Objective
- Read and understand the entire backend stack end-to-end.
- Find and fix correctness, reliability, security, performance, API-contract, and operational issues.
- Do not stop at analysis: implement fixes directly.
- Preserve existing API behavior unless a change is required to fix a bug or vulnerability.

## Required Scope (Read Everything)
You must inspect all backend-related files and linked integration layers, including but not limited to:
- backend/
- backend/app/
- backend/app/api/
- backend/app/api/v1/
- backend/app/middleware/
- backend/app/schemas/
- backend/tests/
- backend/supabase/
- supabase/
- docs/ (API docs, migration docs)
- Any root config that affects backend runtime (Dockerfile, requirements, env examples, CI workflows)

Also inspect cross-layer contracts used by backend clients:
- web_app/ API usage
- flutter_app/ API usage
- cli_app/ API usage

## Work Style Requirements
- First build a dependency and request-flow map (auth, upload, OCR, analysis, history, health, export).
- Then run static checks and tests.
- Then fix issues in small, reviewable commits.
- After each fix, rerun relevant checks.
- Continue until no high/medium issues remain or explicitly explain blockers.

## Non-Negotiable Constraints
- Do not break existing successful flows.
- Do not remove features unless clearly dead and replaced safely.
- Keep naming and file structure stable unless change is necessary.
- Keep changes minimal and targeted.
- Never expose secrets or keys in code/logs.
- Never add fake mocks in production paths.

## Mandatory Audit Checklist

### 1) API Correctness and Contracts
- Validate every route path, method, status code, and response shape.
- Ensure consistent error payload format across endpoints.
- Confirm request validation and schema typing are strict and accurate.
- Check backward compatibility with existing frontend/Flutter/CLI calls.

### 2) Auth and Session Security
- Review token validation paths and failure handling.
- Verify expired/invalid tokens always return proper auth errors.
- Ensure role checks and protected-route boundaries are correct.
- Confirm no auth bypass in optional or fallback branches.

### 3) Upload + OCR Pipeline Safety
- Validate file type and size controls server-side.
- Ensure temporary file handling is safe and cleaned up.
- Audit OCR provider switching/fallback logic for correctness.
- Ensure processing state updates cannot leak data across users/jobs.

### 4) Data Integrity and Database Layer
- Audit SQL queries, ORM usage, and migration consistency.
- Validate indexes and query patterns for key hot paths.
- Ensure transaction safety for multi-step writes.
- Verify null handling, defaults, and enum/value constraints.

### 5) Error Handling and Observability
- Ensure no stack traces leak to API clients.
- Add/normalize structured logs for key failure paths.
- Ensure health endpoints reflect real subsystem state.
- Validate error counters/metrics are accurate and race-safe.

### 6) Concurrency and Resource Management
- Review websocket lifecycle and cleanup behavior.
- Check in-memory maps/caches for leaks and stale data.
- Validate timeout handling and cancellation behavior.
- Ensure no unbounded queues or blocking calls in async paths.

### 7) Performance and Scalability
- Identify N+1 query patterns and repeated expensive calls.
- Reduce redundant serialization/parsing.
- Validate compression and response-size handling.
- Confirm startup path is efficient and robust.

### 8) Configuration and Deployment Readiness
- Validate environment variable loading and defaults.
- Ensure production-safe defaults for CORS, rate limits, and debug flags.
- Validate Docker/Procfile/runtime commands.
- Ensure CI workflows run the right tests and checks.

### 9) Test Quality and Coverage
- Run existing tests first and capture baseline.
- Add missing tests for every bug fixed.
- Cover happy path + auth failure + malformed input + edge cases.
- Ensure deterministic tests (no flaky timing dependence).

### 10) Documentation Fidelity
- Update API/documentation only when behavior changes.
- Keep migration docs aligned with actual schema behavior.
- Add concise notes for any operational changes.

## Required Commands (Adapt as needed)
Run and report outputs for the equivalent of:
- Python dependency install
- Backend test suite
- Lint/type checks (if configured)
- Any migration/schema validation checks
- Health endpoint smoke checks

## Fix Prioritization Policy
- Priority 1: Security vulnerabilities, auth bypass, data corruption, crashers.
- Priority 2: Contract mismatches, race conditions, resource leaks, bad defaults.
- Priority 3: Reliability/perf improvements with low risk.

## Output Format (Strict)
Return results in this order:
1. Executive summary (what was broken, what was fixed).
2. Findings by severity with file paths and exact rationale.
3. Implemented changes list grouped by feature area.
4. Test/check results with pass/fail counts.
5. Remaining risks or deferred items with clear reason.
6. Final production readiness verdict (Go / No-Go) with justification.
7. Also update the #deep_audit_report.md file.

## Completion Criteria
Do not declare done until all are true:
- No unresolved high severity issues.
- All relevant tests pass.
- API contracts verified against existing clients.
- Documentation updated where required.
- Backend is deploy-ready with explicit confidence statement.

If any blocker prevents completion, provide:
- Exact blocker
- Impact
- Minimal next action to unblock
- Safe temporary mitigation
