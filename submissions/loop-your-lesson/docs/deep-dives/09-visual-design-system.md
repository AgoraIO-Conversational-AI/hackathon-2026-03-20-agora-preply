# Visual design system

> Visual language for Lesson Intelligence, informed by Preply's production site, modern chat UX conventions, and education-specific accessibility needs.

## At a glance

**What this covers**: Colors, typography, spacing, radius, elevation, animation, interaction states, and accessibility rules for every UI surface.

**Why it matters**: Teachers use this between lessons - often on a side panel while prepping. The UI must be scannable, trustworthy, and visually consistent with Preply's brand so it feels like a native product, not a hackathon prototype.

**Key terms**:

| Term | Meaning |
|------|---------|
| Token | A named CSS custom property (e.g. `--color-primary`) that encodes a design decision |
| Semantic naming | Tokens named by purpose (`--color-danger`) not appearance (`--color-red`) |
| Surface | A background layer - pages, cards, bubbles, inputs |
| Elevation | Visual depth communicated through shadow intensity |
| Progressive disclosure | Show summary first, reveal detail on interaction |

**Prerequisites**: [frontend-ux.md](08-frontend-ux.md) for widget behavior and message types.

---

## Design inspiration

**Preply production site** - the primary visual reference:
- Coral for all primary CTAs and active states
- White card surfaces on light gray page backgrounds
- Clean sans-serif typography with heavy headings
- Generous internal padding on cards, clear visual grouping
- Thin 1px borders, never heavy outlines
- Rounded corners everywhere - nothing sharp

**Chat UX conventions** (WhatsApp, iMessage, Intercom):
- User messages right-aligned in brand color, assistant left-aligned in neutral
- Asymmetric bubble rounding - the "tail" corner is sharp, others are round
- Timestamps small and muted, never competing with content
- New messages animate in from below

**PostHog Max AI** - structural influence:
- ProcessTimeline for showing AI reasoning steps
- Collapsible tool calls with status indicators
- Progressive disclosure of technical detail

**Tailwind CSS v4** - implementation approach:
- All tokens as CSS custom properties in `:root`, not in Tailwind config
- Utility-first with bracket notation: `bg-[var(--color-primary)]`
- Enables future runtime theming without rebuild

---

## Color system

All colors are defined as CSS custom properties. Components never use raw Tailwind color classes (`bg-red-50`, `text-gray-700`). Every color has a semantic name.

### Brand

| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#ff7aac` | Primary buttons, links, active states, user message bubbles |
| `--color-primary-hover` | `#fe9fc3` | Hover state - lighter, not darker (Preply convention) |
| `--color-primary-light` | `#ffe5f0` | Light background for primary highlights, selected states |

Pink is Preply's signature CTA color. Buttons use **dark text on pink** (not white). Hover goes **lighter** (softer pink), not darker - the opposite of most design systems. This is intentional and matches Preply's production site.

### Accent

| Token | Value | Usage |
|-------|-------|-------|
| `--color-accent` | `#8b8fa3` | Send button, secondary interactive accents |
| `--color-accent-hover` | `#6e7191` | Hover for accent elements |
| `--color-accent-light` | `#f0f0f5` | Avatar backgrounds, subtle highlights |

Lavender accent provides calm contrast to the energetic coral. Used for secondary interactions.

### Text

| Token | Value | Usage |
|-------|-------|-------|
| `--color-text-primary` | `#1b1439` | Headings, names, important content |
| `--color-text-secondary` | `#585271` | Body text, descriptions, secondary labels |
| `--color-text-muted` | `#9896a3` | Timestamps, counts, hints, disabled text |

Three levels only. If you need a fourth, the hierarchy is wrong.

### Surfaces

| Token | Value | Usage |
|-------|-------|-------|
| `--color-surface` | `#ffffff` | Cards, message bubbles, inputs, dropdowns |
| `--color-surface-secondary` | `#f4f4f5` | Page background, badge backgrounds, code result blocks |
| `--color-surface-hover` | `#fafafa` | Hover state for list items and rows |
| `--color-message-other` | `#f4f4f5` | Assistant message bubble background |

Page background is always `surface-secondary`. Content floats on `surface`.

### Borders

| Token | Value | Usage |
|-------|-------|-------|
| `--color-border` | `#e4e4e7` | Container borders, input borders, pill outlines |
| `--color-border-focus` | `#bbb8c9` | Input focus border |

Two border widths, strictly separated:

- **`border-2` (2px)**: All containers and interactive elements - cards, widgets, inputs, dropdowns, buttons, pills, alert boxes. Matches Preply's production tutor cards (`border: 2px solid`).
- **`border` (1px)**: Internal dividers only - `border-t`, `border-b`, `border-r` separating sections within a container. Layout separators (sidebar edge, header bottom).

Never use 1px for a container's outer border. Never use 2px for an internal divider.

### Status

| Token | Value | Usage |
|-------|-------|-------|
| `--color-success` | `#00b37e` | Completed states, correct answers, positive badges |
| `--color-warning` | `#f5a623` | Attention flags, moderate severity, approval dialogs |
| `--color-danger` | `#e5384f` | Errors, failed states, major severity |
| `--color-success-light` | `#ecfdf5` | Success badge/alert background |
| `--color-warning-light` | `#fffbeb` | Warning badge/alert background |
| `--color-danger-light` | `#fef2f2` | Error badge/alert background |

Every status color has a light variant for backgrounds. Use the solid color for text/icons, the light variant for the container behind them.

### Code blocks

| Token | Value | Usage |
|-------|-------|-------|
| `--color-code-bg` | `#1e1e2e` | Code block and tool argument backgrounds |
| `--color-code-text` | `#a6e3a1` | Code block text |

Dark-on-light code blocks. Catppuccin-inspired for readability.

### Severity

| Token | Value | Usage |
|-------|-------|-------|
| `--color-severity-minor` | `#e0f2f1` | Minor error background |
| `--color-severity-moderate` | `#fff3e0` | Moderate error background |
| `--color-severity-major` | `#fce4ec` | Major error background |

Used specifically in error analysis context for pedagogical severity levels.

---

## Typography

### Font

**Inter** loaded via Google Fonts CDN (weights 400, 500, 600, 700). Inter is the open-source base of Preply's proprietary PreplyInter - same metrics and feel, freely available. Declared as `--font-sans` with system-ui fallbacks.

Anti-aliasing is enabled globally (`-webkit-font-smoothing: antialiased`) for crisper rendering on macOS, matching Preply's production site.

### Type scale

Six semantic roles, inspired by Material Design's type system and sized for a chat UI. Each role defines size, line-height, and letter-spacing as a unit - never mix properties across roles.

| Role | Token | Size | Line height | Letter spacing | Usage |
|------|-------|------|-------------|----------------|-------|
| **Display** | `--text-display` | 24px | 32px | -0.01em | Empty state headlines |
| **Title** | `--text-title` | 18px | 28px | -0.005em | Section headings, showcase |
| **Subtitle** | `--text-subtitle` | 15px | 22px | 0em | Widget titles, button md text |
| **Body** | `--text-body` | 14px | 22px | 0.005em | Messages, descriptions, default |
| **Label** | `--text-label` | 12px | 16px | 0.01em | Badges, timestamps, chips |
| **Micro** | `--text-micro` | 10px | 14px | 0.0125em | Utterance counts, tool durations, type tags |

Body is the default - set on `<body>` and inherited everywhere. Only apply a different role explicitly when the text serves a different purpose.

### Letter-spacing philosophy

Borrowed from both Preply's production CSS and Material Design:

- **Large text → negative tracking** (tightens). Display and title text pulls letters closer for a premium, confident feel. Preply uses -0.32px on h1.
- **Body text → near-zero tracking**. Neutral, optimized for readability at reading distance.
- **Small text → positive tracking** (opens). Label and micro text spreads letters apart for legibility at small sizes. Preply uses +0.12px on captions.

This creates a subtle but perceptible typographic hierarchy beyond just size and weight.

### Weight rules

| Weight | Tailwind | When to use |
|--------|----------|-------------|
| 400 | `font-normal` | Body text, descriptions, message content |
| 500 | `font-medium` | Labels, topic names, interactive text, corrected errors |
| 600 | `font-semibold` | Headings, author names ("Preply AI"), widget titles, buttons |

Semibold is the ceiling. Preply's production `ButtonBase` uses 600, not 700.

---

## Spacing and layout

### Spacing conventions

- **Card internal padding** comes in three tiers: `p-3` (compact), `p-4` (standard), `p-6` (spacious)
- **Widget sections** use `px-3 py-2` for headers, `px-4 py-3` for content areas
- **Vertical rhythm between messages**: `space-y-5` - generous enough to scan, tight enough to feel like a conversation
- **Inline element gaps**: `gap-1` to `gap-2` for tight groups (badge + text), `gap-3` for distinct items (avatar + content)

### Width constraints

| Context | Max width | Why |
|---------|-----------|-----|
| Chat messages | `max-w-3xl` | Keeps lines readable, centers in wide views |
| Showcase / docs | `max-w-5xl` | Wider for grid layouts |
| User message bubble | `max-w-[75%]` | Prevents wall-of-text on wide screens |
| Mode dropdown | `w-64` | Fixed width for consistency |

### Layout structure

The app is a horizontal split: optional sidebar (`w-64`) + main content area. The chat area is a vertical flex: scrollable messages + fixed input at bottom.

---

## Border radius

Defined as CSS custom properties for consistency across all components.

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Small interactive elements, focus ring insets |
| `--radius-md` | 8px | Badges, code blocks, action buttons, reasoning panels |
| `--radius-lg` | 12px | Cards, widgets, dropdowns, primary buttons |
| `--radius-xl` | 16px | Message bubbles, chat input container, status alerts |
| `--radius-full` | pill | Chips, suggestion pills, date separators, vocabulary tags |

**Message bubble rule**: Bubbles use `rounded-2xl` (16px) on three corners, with the "tail" corner at `rounded-tr-sm` (user) or `rounded-tl-sm` (assistant). This creates the conversational feel of chat apps.

---

## Shadows and elevation

Three levels. Nothing else.

| Level | Class | Usage |
|-------|-------|-------|
| Resting | `shadow-sm` | Cards at rest, input container |
| Interactive | `shadow-md` | Card/widget on hover, focused elements |
| Floating | `shadow-lg` | Dropdowns, overlays |

Widgets and interactive cards transition between resting and interactive: `transition-shadow hover:shadow-md`. This gives tactile feedback without motion.

---

## Animation

### Keyframes

| Animation | Duration | Easing | Effect | Usage |
|-----------|----------|--------|--------|-------|
| `fadeIn` | 150–200ms | ease-out | Opacity 0→1, translateY(4px→0) | New messages, dropdown open, expanded details |
| `expandDown` | 150ms | ease-out | Opacity 0→1, max-height 0→500px | Collapsible widget sections, theme card content |

### Built-in Tailwind animations

| Animation | Usage |
|-----------|-------|
| `animate-spin` | Loading spinners (Spinner component, tool running indicator) |
| `animate-pulse` | Streaming cursor in assistant messages |

### Duration rules

- **Micro-interactions** (dropdown open, detail expand): 100–150ms. Fast enough to feel instant.
- **Content transitions** (message appear): 200ms. Noticeable but not slow.
- **Never exceed 300ms** for UI transitions. This is a productivity tool, not a marketing site.
- **Always use `ease-out`**. Content appears quickly and settles - the opposite of `ease-in` which feels sluggish.

---

## Interaction states

### Preply border pattern

All interactive bordered elements follow the same pattern from Preply's production site:

- **Default**: `border-2 border-[--color-border]` (light gray, `#e4e4e7`)
- **Hover**: `border-[--color-text-primary]` (near-black, `#1b1439`)

The border darkens on hover - not the background. This is Preply's signature interaction: subtle at rest, confident on hover. Applied to secondary buttons, suggestion chips, filter pills, and any outlined interactive element.

Primary buttons use the same `border-2` with `border-[--color-text-primary]` (dark) - the dark border on pink gives the button a defined, confident edge.

### Buttons

Matched to Preply's production button component (`ButtonBase`).

**Sizing** uses fixed min-heights, not just padding:

| Size | Min height | Horizontal padding | Font size | Letter spacing |
|------|-----------|-------------------|-----------|---------------|
| sm | 40px | 16px | 14px | 0.0125em |
| md | 48px | 24px | 15px | 0.005em |
| lg | 56px | 32px | 16px | 0 |

**Radius**: `--radius-md` (8px) - Preply uses 8px for buttons, not the 12px used for cards.

**Font weight**: `font-semibold` (600) - matches Preply's production `ButtonBase`.

**Transition**: 220ms with `cubic-bezier(0.22, 1, 0.36, 1)` - Preply's snappy ease-out curve.

**All buttons have `border-2`** - even primary. This keeps vertical rhythm consistent between variants.

Four button variants, matching Preply's production `ButtonBase`:

| Variant | Border | Background | Hover |
|---------|--------|------------|-------|
| **Primary** | Dark (`--color-text-primary`) | Pink (`--color-primary`) | Lighter pink |
| **Secondary** | Dark (`--color-text-primary`) | Transparent | Faint tint `rgba(71,71,133,0.06)` |
| **Tertiary** | Subtle (`rgba(20,20,82,0.15)`) | Transparent | Same faint tint |
| **Ghost** | None (transparent) | Transparent | Light gray bg |

Primary = "Book trial lesson". Secondary = bold outline CTA. Tertiary = "Send message" (gentle). Ghost = toolbar actions.

All variants share the same active state (slightly stronger tint) and disabled state (gray bg, muted text).

### Expandable sections

All collapsible sections (widget content, theme cards, thinking blocks, tool call details) follow the same pattern:

1. **Trigger**: A `<button>` element (never a div with onClick)
2. **Icon**: `ChevronRight` that rotates 90° on expand (`transition-transform`)
3. **Focus ring**: `focus-visible:ring-2 ring-[var(--color-primary)] ring-offset-1`
4. **ARIA**: `aria-expanded={expanded}` on the trigger
5. **Animation**: Content appears with `fadeIn` or `expandDown`

This consistency means users learn the interaction once and recognize it everywhere.

### Hover effects

| Element | Hover treatment |
|---------|----------------|
| Widget containers | `shadow-sm` → `shadow-md` |
| List rows (themes, conversations) | Background shifts to `--color-surface-hover` |
| Secondary buttons / chips | Border darkens: `--color-border` → `--color-text-primary` |
| Text buttons (reasoning toggle) | Text shifts from `--color-text-muted` to `--color-primary` |

### Input focus

Chat input container gets `border-[var(--color-border-focus)]` and `shadow-sm` on `focus-within`. The border color darkens subtly - enough to show focus, not enough to shout.

---

## Component behavior

### Message bubbles

| Property | User | Assistant |
|----------|------|-----------|
| Alignment | Right | Left |
| Background | `--color-primary` (coral) | `--color-message-other` (light gray) |
| Text color | White | `--color-text-primary` |
| Tail corner | Top-right (sharp) | Top-left (sharp) |
| Other corners | 16px rounded | 16px rounded |
| Max width | 75% of container | Full width (with avatar) |
| Entry animation | `fadeIn` 200ms | `fadeIn` 200ms |

Assistant messages include an avatar (logo in a rounded `--color-accent-light` circle) and a "Preply AI" name label. User messages have neither.

### Badges

Badges use semantic color mapping - the variant name maps directly to a status meaning:

| Variant | Background | Text color | Meaning |
|---------|------------|------------|---------|
| default | `--color-surface-secondary` | `--color-text-secondary` | Neutral metadata |
| success | `--color-success-light` | `--color-success` | Positive state |
| warning | `--color-warning-light` | `--color-warning` | Needs attention |
| error | `--color-danger-light` | `--color-danger` | Problem state |
| highlight | `--color-highlight-gradient` (blue→pink, from Preply production) | `--color-text-primary` | Sparkles icon + emphasis |

All badges: `rounded-[--radius-md]`, `px-2.5 py-1`, `text-xs font-medium`.

### Cards

Cards are the basic content container. White surface, thin border, subtle shadow.

- Static cards: `shadow-sm` always, no hover change
- Interactive cards: Add `transition-shadow hover:shadow-md` for clickable/hoverable cards

### Widgets

Widgets (ErrorAnalysis, ThemeMap, PracticeCard) are specialized cards with:
- Bordered container with `--radius-lg`
- `hover:shadow-md` transition on the entire widget
- Collapsible body separated by `border-t`
- Header with title + metadata on left, controls on right

### Error and warning alerts

| Type | Border | Background | Icon |
|------|--------|------------|------|
| Error | `--color-danger` | `--color-danger-light` | `AlertCircle` |
| Warning/approval | `--color-warning` | `--color-warning-light` | None (text is enough) |

Error alerts always include an icon. Warning/approval states rely on the amber color to communicate urgency.

### Process timeline

The timeline shows AI reasoning inside the message bubble:
- **Thinking blocks**: Lightbulb icon, muted text, collapsible
- **Tool calls**: Clipboard icon, tool name as label, status icon (spinner → check/x)
- **Status messages**: Spinner + text, only shown while active
- **Nested detail**: Tool arguments render in `--color-code-bg` code blocks, results in `--color-surface-secondary` blocks

---

## Accessibility

### Focus management

Every interactive element must have a visible focus indicator when navigated via keyboard:
- `focus-visible:outline-none` (remove browser default)
- `focus-visible:ring-2` (2px ring)
- `focus-visible:ring-[var(--color-primary)]` (coral ring color)
- `focus-visible:ring-offset-1` (1px gap between element and ring)

Use `focus-visible` not `focus` - mouse users don't need focus rings.

### ARIA attributes

| Pattern | Required attributes |
|---------|-------------------|
| Expandable section | `aria-expanded={boolean}` on the trigger button |
| Dropdown trigger | `aria-expanded={boolean}`, `aria-haspopup="listbox"` |
| Logo SVG | `aria-label="Preply"` |

### Semantic HTML

- All clickable expand/collapse triggers are `<button>`, never `<div onClick>`
- Links use `<a>` with `target="_blank" rel="noopener noreferrer"` for external URLs
- Lists use semantic markup or clear visual structure (not just divs)

### Color contrast

The text/surface combinations maintain readable contrast:
- `--color-text-primary` (#1b1439) on `--color-surface` (#fff) - high contrast
- `--color-text-secondary` (#585271) on `--color-surface` - readable for body text
- `--color-text-muted` (#9896a3) on `--color-surface` - acceptable for non-essential metadata
- White text on `--color-primary` (#f85f73) - sufficient for button labels

---

## Icon system

All icons come from **lucide-react**. No mixing icon libraries.

### Standard sizes

| Size | Class | Usage |
|------|-------|-------|
| 10px | `h-2.5 w-2.5` | Micro icons inside pills |
| 12px | `h-3 w-3` | Inline metadata (clock, chevron in small context) |
| 14px | `h-3.5 w-3.5` | Tool call status icons, thinking indicators |
| 16px | `h-4 w-4` | Standard UI icons (navigation, expand/collapse) |
| 24px | `h-6 w-6` | Logo in empty state |

Always add `shrink-0` to icons in flex containers to prevent them from compressing.

---

## Showcase page

`/showcase` is the living reference for the design system. It renders every component, state, and variant on a single page - the source of truth for how things actually look.

Sections: primitives (colors, badges, buttons, spinners, cards, animations), mode selector, chat input states, message types, conversation states (empty, connecting, thinking, error, approval), widgets, and a full conversation flow.

When adding new components or visual patterns, add them to the showcase first.
