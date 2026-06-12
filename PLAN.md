# Frontend redesign plan

## Goal
Redesign the current Next.js Phase 1 account-access page into a premium white landing/auth experience inspired by the structure and polish of the provided references, while preserving all existing auth/session behavior and the approved Phase 1 UI contract.

## Design direction
- **Aesthetic:** calm editorial minimalism with AI-product clarity
- **Primary canvas:** pure white
- **Linework:** thin pale-cyan / light-blue borders and dividers
- **Brand accent:** use a simplified mark derived from `Brand_identity.png` as a restrained terracotta signature in the logo/icon/favicon, not as the page’s dominant color
- **Reference synthesis:** use ChatGPT/Unsloth for hierarchy and product confidence, and `style_that_i_want.png` for spacing rhythm, rounded panels, and premium composition
- **Constraint:** keep this as a polished account-access landing page, not a fake chatbot/dashboard shell

## Planned changes

### 1. Keep core auth behavior intact
Do not change the meaning of the current flows in `frontend/lib/auth-session.ts`.
- preserve session restore, login, register, refresh, logout, and fail-closed handling
- keep `frontend/app/page.tsx` thin, continuing to resolve `?mode=register`
- treat the redesign as presentation/component refactoring around the existing controller

### 2. Refactor `AccountAccessShell` into a composition root
Update `frontend/components/account-access/AccountAccessShell.tsx` so it mainly:
- owns client state and form handlers
- manages readiness bootstrap and visible-only polling
- manages mode switching, document title, and alert/focus flow
- renders smaller UI-spec-aligned subcomponents instead of all markup inline

### 3. Split the page into dedicated account-access components
Add the missing UI contract components so styling and logic are cleaner:
- `AuthCard.tsx`
- `AuthModeSwitch.tsx`
- `FormField.tsx`
- `PasswordField.tsx`
- `InlineAlert.tsx`
- `PlatformStatus.tsx`
- `SecuritySummary.tsx`
- `CurrentUserCard.tsx`
- `StatusBadge.tsx`
- `ScopeList.tsx`
- `DemoAccountPanel.tsx`

These will preserve the current IA:
- left/context column: brand, hero statement, security summary, readiness
- right/content column: auth card or authenticated current-user card

### 4. Rework the visual system in `globals.css`
Rewrite the global tokens/classes in `frontend/app/globals.css` to match the requested look:
- white page background
- pale-cyan borders and separators
- softer shadows and more generous whitespace
- refined card surfaces
- stronger visual rhythm for headings, sections, and forms
- preserved accessibility, reduced-motion, and touch-target rules from `01-UI-SPEC.md`

### 5. Upgrade `BrandLockup` into a stronger hero block
Update `frontend/components/account-access/BrandLockup.tsx` to:
- keep the approved Vietnamese copy
- introduce a more memorable brand mark treatment
- support a premium hero composition without adding non-phase UI
- reuse the same mark language that will drive the favicon/app icon

### 6. Implement exact readiness UI mapping
Create `frontend/lib/readiness.ts` plus `PlatformStatus.tsx` to centralize:
- ready / degraded / not-ready / disconnected states
- exact Vietnamese labels/body copy from the UI spec
- component-state label mapping
- visible-only 60-second polling behavior and retry wiring from the shell
- mobile disclosure vs desktop expanded detail behavior

### 7. Implement the authenticated identity card cleanly
Move the current authenticated block into `CurrentUserCard.tsx` and `ScopeList.tsx`:
- safe identity fields only from `/api/auth/me`
- role/status badges
- exact scope label + scope code rendering
- phase note and clearly separated logout area

### 8. Add development-only demo account UI safely
Introduce `frontend/lib/demo-config.ts` and `DemoAccountPanel.tsx` to support the Phase 1 demo contract:
- render only when the Next.js server sees both development mode and enabled demo seeding
- fill the login form only, with no auto-submit
- move focus to the login CTA and announce the fill action
- ensure production output contains no demo credentials or hidden leaks

### 9. Create brand-derived icon + favicon assets
Add a simplified icon based on `Brand_identity.png`:
- likely `frontend/app/icon.svg`
- optionally wire icon metadata in `frontend/app/layout.tsx`
- reuse the same simplified mark in the hero lockup for consistency

## Files expected to change
- `frontend/app/page.tsx` (minimal, likely prop wiring only)
- `frontend/app/layout.tsx` (icon/metadata or font-class refinements if needed)
- `frontend/app/globals.css`
- `frontend/components/account-access/AccountAccessShell.tsx`
- `frontend/components/account-access/BrandLockup.tsx`
- new account-access components listed above
- `frontend/lib/readiness.ts`
- `frontend/lib/demo-config.ts`
- targeted frontend tests for readiness/demo helpers if practical

## Verification plan
- run frontend typecheck
- run or add lightweight frontend tests for readiness/demo helper logic
- verify no auth/session behavior regresses
- verify production build does not expose demo values
- visually validate desktop/tablet/mobile composition against the requested references and the existing Phase 1 UI contract

## Key risk controls
- preserve `auth-session.ts` semantics
- avoid introducing any fake chat/dashboard UI
- keep all user-facing copy compatible with `01-UI-SPEC.md`
- keep demo credentials server-gated and absent from production artifacts
- prioritize accessibility and focus behavior while restyling
