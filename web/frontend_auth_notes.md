# Frontend Integration Notes

This backend update adds REST endpoints for authentication (`/api/auth/*`), notes CRUD, and attachment uploads. To finish the feature end-to-end, update the Vite/Vue app as follows:

1. **API client helpers**
   - Create a small wrapper around `fetch` that always sets `credentials: 'include'` and attaches the CSRF header. Read the value from the `csrf_token` cookie (set by `GET /api/auth/csrf`).
   - Handle `401/403` globally so the UI can redirect to a login panel when the session expires.

2. **Auth composable / store**
   - Add `useAuth()` (or Pinia store) that exposes `currentUser`, `memberships`, `login`, `register`, `logout`, and `bootstrapSession`.
   - On app boot, call `/api/auth/csrf` then `/api/auth/me` to reuse an existing session.
   - Keep errors surfaced via `ant-design-vue` message prompts.

3. **Sidebar UI**
   - Add a footer panel (similar to ChatGPT) inside the existing sidebar component that shows:
     - Logged-out state: email/password form with `注册` / `登录` buttons hitting the new endpoints.
     - Logged-in state: avatar/initials, membership badge (`member_plan` & `member_until`), and a logout button.
   - Disable note-related actions until the user is authenticated.

4. **Notes data flow**
   - Replace mock notes arrays with API calls: list via `GET /api/notes`, create/update via the new POST/PUT routes (send CSRF header), and append chat messages via `POST /api/notes/{id}/messages`.
   - Wire attachment uploads through `POST /api/attachments/presign-upload` followed by direct S3 upload using the returned form data. Refresh the note detail afterwards.

5. **Environment config**
   - Store `VITE_API_BASE_URL` pointing to the FastAPI host (e.g. `http://localhost:8000/api`).
   - Ensure `fetch` calls use that base URL and keep `withCredentials` enabled.

6. **CSRF handling**
   - Before any mutating call (register/login/logout/create/update), ensure a fresh CSRF token by calling `/api/auth/csrf` and forwarding it through the `X-CSRF-Token` header.
   - If a call returns `403` due to CSRF failure, refresh the token and retry once.

Implementation tip: encapsulate all HTTP calls in `web/src/services/api.ts` so components stay declarative and focused on rendering.
