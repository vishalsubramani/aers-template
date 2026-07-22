# Grounding — Frontend engineering

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing UI components, client/server state, rendering or performance
strategy, CSS architecture, forms, accessibility, or i18n/l10n work.
**Doctrine hooks:** AX-02, AX-03, AX-05, AX-07, AX-08, AX-11, AX-12, AX-14, AX-17, AX-18, AX-20,
AX-21, AX-22, DD-03, DD-04, DD-06, DD-17, PAT-01, PAT-08, PAT-09, PAT-13, DF-01, DF-04

## Design checklist

- [ ] Which state is server cache vs client state, and who owns its invalidation and staleness
      bound? *(DD-17, PAT-09)*
- [ ] Can any stored state be derived instead, and are impossible UI state combinations
      unrepresentable? *(AX-08)*
- [ ] Where are the error boundaries and loading fallbacks per route region, and what does the
      user see when a call fails or hangs? *(AX-09, AX-11, PAT-08)*
- [ ] Which rendering strategy does each route use, and what is its hydration cost in shipped JS?
- [ ] What are the route's Core Web Vitals and bundle budgets, and which CI gate enforces them?
      *(AX-18, AX-22)*
- [ ] Is client validation mirrored by server validation from one shared schema? *(PAT-01, DD-03)*
- [ ] Is every flow operable by keyboard and screen reader, with a named WCAG level in the
      acceptance criteria?
- [ ] Are all user-facing strings externalized with ICU plurals, and is the layout RTL-safe?
- [ ] Are timestamps stored UTC and rendered per locale, with the future-event and all-day
      exceptions handled? *(DD-06)*
- [ ] Which third-party scripts ship, and what does each cost in main-thread time and privacy
      exposure? *(AX-21)*

## Component architecture and UI modularity

- **Component-driven development** — build and verify components in isolation before pages; a
  component that cannot render without whole-app context has a broken boundary *(AX-03)*.
- **Atomic design (atoms → molecules → organisms → templates → pages)** — use as shared
  vocabulary, not a filing mandate; organize by feature and promote to shared only on the rule
  of three *(AX-17)*.
- **Presentational vs container components** — keep data fetching out of leaf components so they
  stay testable and reusable; hooks blurred the split but the dependency direction still holds
  *(AX-04)*.
- **Composition over configuration (children / slots)** — when a component sprouts boolean and
  variant props, pass children/slots instead; a prop-explosion API is inheritance in disguise
  *(AX-07, AX-05)*.
- **Controlled vs uncontrolled components** — pick one per input and never switch mid-lifecycle;
  half-controlled inputs produce the "value snaps back" bug. Default to controlled for anything
  validated.
- **Unidirectional data flow** — data down, events up; a child writing parent state directly
  makes render order a correctness dependency and updates untraceable *(AX-04)*.
- **State colocation; lift state only when needed** — keep state in the lowest component that
  needs it; premature lifting buys app-wide re-renders and prop drilling for nothing *(AX-17)*.
- **Local vs global state; server cache is not client state** — server data lives in a query/
  cache layer with staleness and invalidation rules, never copied into a global store *(DD-17,
  PAT-09)*.
- **Derived state** — compute it during render from source state; storing a derived copy creates
  a sync obligation that will eventually be missed *(DD-17)*.
- **Prop drilling vs context vs stores** — escalate in that order: drilling two or three levels
  is fine, context for stable app-wide values, a store only when update frequency proves it
  *(AX-17)*.
- **State machines & statecharts** — once more than two booleans describe one status, model
  explicit states so `loading && error && success` cannot be constructed *(AX-08)*.
- **Immutability in state updates** — in-place mutation breaks change detection and memoization
  silently; treat state as immutable everywhere, not just where the framework complains
  *(AX-12)*.
- **Keys & reconciliation; the virtual DOM** — index-as-key on reorderable or filterable lists
  corrupts input and animation state; keys must be stable identity, never position *(DD-04)*.
- **Memoization & referential-equality footguns** — any inline object, array, or closure prop
  defeats memo; profile before and after instead of sprinkling it everywhere *(AX-18)*.
- **Error boundaries** — place one per route or feature region so one widget's crash cannot
  blank the app; report the component stack to observability *(AX-11, AX-14, PAT-08)*.
- **Suspense & streaming UI** — design fallbacks per region, not per component; nested suspense
  hides request waterfalls — hoist data fetching to the route.
- **Render props / HOCs / hooks** — know which era the codebase is in and do not mix them; new
  abstractions use hooks, HOC wrappers are legacy to migrate, not extend *(AX-02)*.
- **Design systems & design tokens** — hardcoded colors and spacing are the frontend's magic
  numbers; tokens are the design–code contract, so token renames are breaking changes *(AX-06)*.
- **Theming (dark mode is a token problem)** — theme by swapping semantic token values, never
  per-component conditionals; if dark mode requires component edits, the token layer failed.
- **Component workshops (Storybook-style)** — a component that cannot render in the workshop has
  hidden dependencies; the workshop doubles as visual-regression surface and living docs
  *(AX-03)*.
- **Micro-frontends & module federation** — pay the coordination tax (version skew, duplicate
  deps, design-system drift) only for genuinely independent team deployment; default is one
  build *(DF-01, AX-17)*.
- **CSS architecture (BEM, ITCSS, CSS Modules, utility-first, CSS-in-JS)** — pick one convention
  repo-wide and enforce scoping; runtime CSS-in-JS charges render-time cost per element, prefer
  build-time extraction *(AX-01)*.
- **Specificity & cascade layers** — an `!important` escalation war means the architecture
  failed; use `@layer` or scoped styles so declared order, not specificity, decides.
- **Container queries** — components that adapt to their container, not the viewport, stay
  reusable across layouts; reach for them before duplicating breakpoint variants.
- **Debounce vs throttle** — debounce waits for quiet (search input); throttle caps the rate
  (scroll, resize); the wrong one makes the UI feel dead or floods the network.
- **Optimistic UI with rollback** — only for high-success mutations with a designed rollback and
  error surface; optimism without rollback is lying to the user *(AX-11)*.
- **Skeleton screens vs spinners** — skeletons for known layout (they cut perceived wait and
  layout shift), spinners for indeterminate work; show neither before ~300 ms to avoid flash.
- **Virtualized lists** — render only the visible window past a few hundred rows, but
  virtualization breaks find-in-page and screen readers — measure the need first *(AX-18)*.
- **Form state & schema validation** — one schema drives client validation, messages, and types;
  client checks are a courtesy — the server revalidates everything *(PAT-01, DD-03)*.
- **Feature detection over browser sniffing** — test the capability, never the user-agent
  string; UA sniffing rots as browsers evolve and misclassifies the ones you never tested.

## Frontend performance

- **Core Web Vitals (LCP, INP, CLS; plus TTFB, FCP)** — budget these per route and treat them as
  frontend SLIs: alert on field regressions, not vibes *(AX-22, AX-18)*.
- **Rendering strategies (CSR, SSR, SSG, ISR, islands, server components)** — choose per route
  by content freshness and interactivity, not one global mode; SSR buys first paint and charges
  server plus hydration cost *(AX-18)*.
- **Hydration cost; partial & progressive hydration** — HTML that paints fast but hydrates slow
  trades LCP for dead-feeling INP; ship less JS or island-ize before tuning hydration order.
- **Code splitting & route-level chunks** — split at routes and heavy below-the-fold widgets;
  preload on intent (hover, viewport) so splitting does not add click latency.
- **Tree shaking & dead-code elimination** — barrel files and side-effectful imports silently
  defeat it; verify with bundle analysis rather than assuming the bundler did it *(AX-20)*.
- **Bundle analysis & performance budgets** — enforce size budgets in CI so regressions fail the
  build; a budget without a gate is a wish *(AX-18)*.
- **Image optimization (responsive srcset, modern formats, lazy loading)** — images dominate
  page weight, but never lazy-load the LCP image — that is the classic self-inflicted
  regression.
- **Font loading (FOIT/FOUT, font-display)** — set `font-display: swap|optional`, preload and
  subset critical fonts; invisible text waiting on a webfont is a chosen outage.
- **Third-party script cost; facades** — every third-party tag is unbounded main-thread and
  privacy liability; load behind a facade or after interaction, and audit tags like
  dependencies *(AX-21)*.
- **Long tasks & the main-thread budget** — any task over 50 ms blocks input; chunk work with
  yields or move it to a worker — the main thread is the app's scarcest resource.
- **RUM vs lab data** — lab runs (Lighthouse) gate regressions; only field RUM proves real-user
  experience across devices and networks. Ship both, decide on RUM *(AX-14, PAT-13)*.

## Accessibility and internationalization

- **Semantic HTML first; ARIA second** — native button/label/list elements get keyboard and
  screen-reader behavior free; wrong ARIA is worse than none — add it only when no element
  fits.
- **WCAG levels** — name the target level (AA is the usual floor) in acceptance criteria;
  "accessible" without a level is untestable *(AX-22)*.
- **Keyboard navigation, focus management, tab order, skip links** — every flow must work
  mouse-free: modals trap and restore focus, route changes move it, DOM order is tab order,
  skip links precede repeated nav.
- **Color contrast; prefers-reduced-motion** — enforce contrast at the design-token level so it
  cannot regress per component; honor reduced-motion — it is vestibular safety, not
  preference.
- **Screen reader testing** — automated checkers catch under half of accessibility issues; walk
  critical flows with a real screen reader before claiming them accessible *(AX-16)*.
- **Accessible forms (labels, error announcements)** — every input gets a programmatic label;
  errors link via `aria-describedby` and announce through a live region, not just red paint.
- **i18n (ICU messages, pluralization rules, RTL layouts)** — never concatenate translated
  fragments; ICU owns plural and gender forms; use logical properties from day one — RTL
  retrofits are rewrites.
- **Locale-aware dates, numbers, currencies** — format with the platform `Intl` APIs at the
  render edge; hand-rolled formatting is one bug per locale *(DF-04, AX-21)*.
- **Store UTC, render local — and the exceptions** — persist UTC and format per viewer *(DD-06)*,
  but future events need the IANA zone (rules change) and all-day dates are calendar dates,
  not instants.
- **Unicode (normalization, grapheme clusters vs code points)** — normalize (NFC) before
  comparing or deduplicating; truncating by code points splits emoji and accents — count
  graphemes for user-visible text.
