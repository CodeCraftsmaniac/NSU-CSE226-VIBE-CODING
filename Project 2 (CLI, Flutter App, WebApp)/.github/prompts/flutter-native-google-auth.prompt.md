---
name: Flutter Native Google Auth (NSU)
description: "Implement native Google-only auth in flutter_app by mirroring nsu_nexus_app"
argument-hint: "Optional constraints (for example: keep backend API contract unchanged)"
agent: agent
---
Implement native Google-only authentication for this workspace's flutter client.

Scope:
- Edit only flutter_app unless a required configuration dependency is missing.
- Do not modify CLI, web_app, or backend auth flows unless explicitly required.

Reference implementation:
- [nsu_nexus_app Google auth service](../../nsu_nexus_app/lib/services/auth/supabase_auth_service.dart)

Requirements:
1. Use native Google account picker UX (Perplexity-style), not browser/device-code flow.
2. Keep Google as the only sign-in method.
3. Mirror the reference flow:
   - `GoogleSignIn(serverClientId: ...)`
   - retrieve `idToken` (and access token when available)
   - exchange with Supabase via `signInWithIdToken`
   - persist session token and user profile
   - support full logout (local session + Google sign-out)
4. Reuse existing package/config where possible (`google-services.json`, package id, OAuth credentials).
5. Ensure all auth-consuming screens use one consistent auth service/state.
6. Preserve existing app styling and navigation behavior.
7. Provide friendly errors for:
   - config error (`ApiException: 10` / `DEVELOPER_ERROR`)
   - cancelled sign-in
   - network/auth backend failures
8. Run static checks on touched files and resolve new compile issues.

Response format:
- Files changed
- Why each change was made
- Verification commands run and result
- Manual setup still required (if any), especially SHA-1 / OAuth client setup
