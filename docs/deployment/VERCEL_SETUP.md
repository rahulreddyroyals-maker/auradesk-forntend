# Vercel Setup

## 1. Create the project

1. Push this repository to GitHub (if not already).
2. In Vercel: New Project → Import the repo.
3. **Root Directory**: set to `frontend` (this is a monorepo — Vercel
   needs to know the Next.js app isn't at the repo root).
4. Framework preset: Next.js (auto-detected).
5. Build command: `npm run build` (matches `vercel.json`, auto-detected
   anyway).

## 2. Environment variables

Add the three frontend variables from `ENVIRONMENT_VARIABLES.md` under
Project Settings → Environment Variables. Set them for Production (and
Preview, pointed at a staging backend if you stand one up — not
required to launch).

## 3. Production domain

Project Settings → Domains → add `app.auradesk.com` (or your actual
domain). Vercel will show the DNS record to add — see `DNS_SETUP.md`.

## 4. Preview deployments

On by default for every PR/branch push. No extra config needed. Make
sure Preview environment variables point at a non-production
`NEXT_PUBLIC_API_BASE_URL` if you don't want preview builds hitting
production data — Railway can host a second, cheaper backend instance
for this if you want it, or preview deployments can just point at the
same production API (acceptable for a small team, worth revisiting as
you scale).

## 5. Before going live — verified this pass

- `npm run build` succeeds — confirmed locally, all 27 routes compile.
- TypeScript passes — confirmed, part of the build.
- ESLint passes — confirmed, part of the build (Next.js runs it during
  build by default).
- No `NEXT_PUBLIC_`-prefixed secret exists in the codebase — confirmed
  by grep.
- Security headers configured (`next.config.js`) — added this pass.

## 6. What you still need to do

- Actually create the Vercel project and connect the GitHub repo (I
  don't have access to create this on your behalf).
- Add the production domain and verify DNS.
- Confirm the deployed app can reach the Railway backend (CORS —
  `FRONTEND_ORIGINS` on the backend must include the exact Vercel
  production URL/domain).
