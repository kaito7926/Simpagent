# Frontend workspace audit — 2026-06-15

## Scope
- URL reviewed: `http://localhost:8000`
- Session used: local demo admin account (`demo.admin@simpagent.test`)
- Goal: identify UX / IA / frontend-contract issues visible in the current SimpAgent workspace and write actionable notes for the frontend team.

## Evidence captured
- `artifacts/frontend-audit-workspace-full.png`
- `artifacts/frontend-audit-workspace-viewport.png`
- `artifacts/frontend-audit-mobilebar.png`
- `artifacts/frontend-audit-settings-mislabel.png`
- `artifacts/frontend-audit-workspace-snapshot.txt`

## Summary
The current workspace shell is functional enough for local testing, but the frontend still exposes multiple prototype/scaffold surfaces as if they were productized features. The biggest problems are:
1. **Duplicate top-level navigation/chrome on desktop**.
2. **Dead sidebar sections that look real but do nothing**.
3. **Admin controls duplicated across too many places**.
4. **Settings view mislabeled as Orchestration**.
5. **Scaffold/admin placeholder pages shown as first-class product surfaces**.

---

## Findings

### FEA-01 — Desktop shows duplicate global chrome
**Severity:** High  
**Observed in UI:** On desktop, the page shows both the left sidebar chrome **and** the top mobile bar. This duplicates branding and the “new chat” action:
- Sidebar: logo + `Start New Chat`
- Top bar: logo + `New chat`

This makes the layout feel unfinished and creates two competing primary navigations.

**Code evidence**
- `frontend/components/chat/ChatWorkspace.tsx:789-799` renders `ChatSidebar`, `ChatMobileBar`, and `ChatDrawer` together.
- `frontend/components/chat/ChatMobileBar.tsx:13-24` defines a full mobile top bar with brand and CTA.
- `frontend/components/chat/ChatSidebar.tsx:245-289` defines a separate desktop sidebar brand and CTA.

**Why this is a problem**
- Violates information hierarchy: two primary nav systems on one viewport.
- Produces the exact duplication the user flagged.
- Makes desktop look like a mobile-responsive layer was left enabled.

**Recommendation**
- Render `ChatMobileBar` only below the mobile breakpoint.
- Render `ChatSidebar` only for tablet/desktop layouts.
- Keep exactly **one** primary “new chat” CTA visible per viewport.

**Acceptance criteria**
- Desktop: only sidebar chrome is visible.
- Mobile: only mobile bar + drawer entry point are visible.
- No repeated logo / brand / new-chat action on the same viewport.

---

### FEA-02 — Settings page is mislabeled as “Orchestration” in the main header
**Severity:** High  
**Observed in UI:** Clicking **Settings** opens a page whose card title says `Settings`, but the main page header still says `Orchestration`.

**Code evidence**
- `frontend/components/chat/ChatWorkspace.tsx:834-844` builds the admin header title with a switch-like ternary, but there is **no case for `settings`**; it falls through to `"Orchestration"`.
- `frontend/components/settings/SettingsPage.tsx:68-71` clearly titles the card as `Settings`.

**Why this is a problem**
- The user lands on one page but the shell says they are on another.
- Breaks orientation and trust.
- Strong signal that the page-state mapping is incomplete.

**Recommendation**
- Add an explicit `settings` case in the workspace header title/description mapping.
- Consider centralizing page metadata in a single config object instead of nested ternaries.

**Acceptance criteria**
- When `workspaceView === "settings"`, the header title is `Settings`.
- Header description also matches settings context, not orchestration context.

---

### FEA-03 — Sidebar exposes dead placeholder sections as real features
**Severity:** High  
**Observed in UI:** The sidebar shows:
- `PINNED CHATS`
- `FOLDERS`
- `TEMPLATES`

All three look like shipped product features, but currently only display placeholder copy.

**Code evidence**
- Shared placeholder component: `frontend/components/chat/ChatSidebar.tsx:147-153`
- Pinned placeholder: `frontend/components/chat/ChatSidebar.tsx:301-304`
- Folders placeholder: `frontend/components/chat/ChatSidebar.tsx:375-376`
- Templates placeholder: `frontend/components/chat/ChatSidebar.tsx:389-390`

**Why this is a problem**
- Creates false affordances.
- Increases cognitive load in the most important navigation area.
- Makes the app feel like a template rather than a finished product.

**Recommendation**
- Remove these sections entirely until they are implemented.
- If they must remain for roadmap reasons, gate them behind a clear `Coming soon` experimental section, visually distinct from real navigation.

**Acceptance criteria**
- No dead sections appear in production-facing sidebar.
- Users only see navigation items that perform useful actions now.

---

### FEA-04 — Admin controls are fragmented across too many places
**Severity:** High  
**Observed in UI:** The same admin capability (`Trusted supervisor` / Python orchestration control) appears in multiple surfaces:
1. Sidebar footer
2. Chat composer tools menu (`Guardrail agent`)
3. Dedicated `Orchestration` page
4. Settings page (`Administrative Orchestration`)

**Code evidence**
- Sidebar admin toggle: `frontend/components/chat/ChatSidebar.tsx:437-468`
- Composer admin menu item: `frontend/components/chat/ChatComposer.tsx:142-158`
- Orchestration page controls: `frontend/components/chat/ChatWorkspace.tsx:257-297`
- Settings admin summary: `frontend/components/settings/SettingsPage.tsx:215-235`

**Why this is a problem**
- Admin IA is scattered and redundant.
- Users cannot tell which control is the canonical place to manage orchestration.
- Privileged actions appearing inside the chat composer are especially confusing.

**Recommendation**
- Consolidate admin management into **Settings > Administrative controls** (or a dedicated Admin settings section).
- Remove orchestration toggles from the chat composer and sidebar footer.
- Keep the sidebar admin nav for navigation only, not for state mutation.

**Acceptance criteria**
- One canonical place to modify trusted supervisor state.
- Sidebar and composer no longer duplicate the same toggle.
- Admin surfaces follow a predictable hierarchy: navigate in sidebar, configure in settings/admin page.

---

### FEA-05 — Chat composer tools menu mixes end-user tools with admin-only controls
**Severity:** Medium-High  
**Observed in UI:** Opening the `Tools` menu in chat shows:
- `Web Search`
- `Python Sandbox` (disabled)
- `Guardrail agent` (admin control)

**Code evidence**
- Tools menu structure: `frontend/components/chat/ChatComposer.tsx:109-161`
- Disabled Python item: `frontend/components/chat/ChatComposer.tsx:132-140`
- Admin control in same menu: `frontend/components/chat/ChatComposer.tsx:142-158`

**Why this is a problem**
- User-facing tool selection and admin system configuration are different mental models.
- A disabled `Python Sandbox` item suggests a broken feature rather than a deliberate product boundary.
- `Guardrail agent` is an infrastructure/admin concept, not a chat-composer action.

**Recommendation**
- Keep the composer menu strictly user-task-oriented.
- Remove admin controls from the composer.
- Hide disabled features unless there is a strong product need to preview them.
- If Python is not available, present capability state in a dedicated settings/help location rather than as a dead composer action.

**Acceptance criteria**
- Composer tools menu contains only actionable user-facing tools.
- No admin-only control appears in the message composer.
- Disabled placeholder tools are either removed or accompanied by explicit explanatory UX.

---

### FEA-06 — Several admin pages are scaffold shells but are presented as shipped pages
**Severity:** Medium-High  
**Observed in UI:** Multiple admin views are visible in navigation but mostly contain placeholders or implementation notes.

**Code evidence**
- Overview hardcoded/placeholder-style metrics and messaging: `frontend/components/chat/ChatWorkspace.tsx:141-146`, `153-155`
- Users page “comes next” empty state: `frontend/components/chat/ChatWorkspace.tsx:199`
- Security events “No security events loaded yet”: `frontend/components/chat/ChatWorkspace.tsx:228`
- Tool executions placeholder: `frontend/components/chat/ChatWorkspace.tsx:233-237`
- Gateway evidence scaffold note: `frontend/components/chat/ChatWorkspace.tsx:249-250`

**Why this is a problem**
- Users see internal roadmap wording (`Phase 5`, `comes next`, `ready for wiring`) inside the product.
- Makes the interface feel unfinished.
- Suggests functionality exists even when it is still a shell.

**Recommendation**
- Hide incomplete admin pages until backed by real data.
- If exposure is necessary for internal testing, add explicit internal-preview labeling.
- Replace roadmap/dev copy with product-ready empty states.

**Acceptance criteria**
- No internal implementation language is shown to normal users/admins.
- Empty states describe user action or current system state, not engineering roadmap.

---

### FEA-07 — Brand naming is inconsistent: `Simpagent` vs `SimpAgent`
**Severity:** Medium  
**Observed in UI:** Different parts of the interface use different capitalization.

**Code evidence**
- Sidebar brand: `frontend/components/chat/ChatSidebar.tsx:249-251` → `Simpagent`
- Mobile bar brand: `frontend/components/chat/ChatMobileBar.tsx:18-24` → `SimpAgent`
- Auth shell copy also mixes variants: `frontend/components/account-access/AccountAccessShell.tsx:89-109`

**Why this is a problem**
- Weakens brand consistency.
- Reinforces the impression of mixed template layers / unfinished polish.

**Recommendation**
- Choose one canonical brand string and centralize it in a shared constant/component.

**Acceptance criteria**
- The same product name appears consistently across auth, workspace, mobile bar, and metadata.

---

### FEA-08 — Admin overview metrics can mislead because presentation implies live production truth
**Severity:** Medium  
**Observed in UI:** Admin metric cards all display a `Live` badge, even when some values are static copy or derived from shell-level placeholders.

**Code evidence**
- Metric card always renders `Live`: `frontend/components/chat/ChatWorkspace.tsx:113-121`
- Example metrics with non-operational copy: `frontend/components/chat/ChatWorkspace.tsx:145-146`

**Why this is a problem**
- “Live” implies verified operational telemetry.
- Some metric content is descriptive or roadmap-oriented rather than measured data.
- This can mislead operators into over-trusting the page.

**Recommendation**
- Only label cards `Live` when backed by actual refreshed backend data.
- Use clearer states such as `Static`, `Derived`, `Unavailable`, or `Preview`.

**Acceptance criteria**
- Badge semantics match actual data provenance.
- No static scaffold card is labeled as live telemetry.

---

## Recommended cleanup order
1. **Fix desktop/mobile chrome duplication** (`FEA-01`)
2. **Fix settings mislabeling** (`FEA-02`)
3. **Remove dead sidebar sections** (`FEA-03`)
4. **Consolidate admin controls into settings/admin config** (`FEA-04`, `FEA-05`)
5. **Hide scaffold admin pages or relabel them as internal preview** (`FEA-06`, `FEA-08`)
6. **Normalize branding** (`FEA-07`)

## Product direction notes
These align with the user’s requested direction:
- Remove or hide `Pinned chat`, `Folders`, `Templates` until they actually work.
- Do **not** keep admin mutation controls in the sidebar footer.
- Move admin functionality into **Settings** (or a dedicated Admin settings area) instead of scattering it across chat surfaces.
- Keep the workspace focused on the primary chat workflow.
