# PipeUHR — Design System

## Design Philosophy

The interface follows a **restrained, data-first** aesthetic. Every element serves readability and task completion. No decorative gradients or visual noise; elevation is subtle and purposeful (soft, theme-aware shadows that aid grouping and signal interactivity, never decoration). The design communicates institutional credibility appropriate for an R&D deliverable reviewed by engineers and regulatory bodies.

## Color Strategy: Restrained

Tinted neutrals with a single accent at less than 10% surface area. The accent (steel blue) references hydraulic engineering without being literal. Uses DaisyUI built-in themes: `winter` (light) and `business` (dark).

### Light Theme (DaisyUI `winter`)

A professional, cool-toned light theme with blue primary accent. Built into DaisyUI with proper OKLCH color values.

| Role | Approximate Hex | Usage |
|------|-----------------|-------|
| Primary | `#047AFF` | Buttons, links, focus rings |
| Secondary | `#463AA2` | Muted UI elements |
| Accent | `#C148AC` | Highlights, secondary actions |
| Background | `#FFFFFF` | Page background |
| Surface | `#F2F7FF` | Cards, table headers |
| Border | `#B3C5EF` | Dividers, input borders |
| Text | `#1C2431` | Body text, headings |
| Success | `#16a34a` | Constraints satisfied |
| Warning | `#d97706` | Partial violations |
| Error | `#dc2626` | Solver failure, constraint violations |

### Dark Theme (DaisyUI `business`)

A professional dark theme with deep neutral backgrounds and readable contrast.

| Role | Approximate Hex | Usage |
|------|-----------------|-------|
| Primary | `#1C4F82` | Buttons, links |
| Background | `#202020` | Page background |
| Surface | `#2A2A2A` | Cards, table headers |
| Border | `#383838` | Dividers, input borders |
| Text | `#D6D6D6` | Body text, headings |
| Success | `#22c55e` | Constraints satisfied |
| Warning | `#f59e0b` | Partial violations |
| Error | `#ef4444` | Solver failure, constraint violations |

## Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Body | `Inter` (system sans fallback) | 14px / 0.875rem | 400 |
| Headings | `Inter` | 18–24px | 600 |
| Data / Numbers | `JetBrains Mono` | 13px / 0.8125rem | 500 |
| Labels | `Inter` | 12px / 0.75rem | 500 (uppercase tracking) |
| Code | `JetBrains Mono` | 13px | 400 |

Line length capped at 72ch for prose blocks. Data tables use full available width.

## Component Standards

### Navigation
- Slim horizontal navbar (h-14), no hamburger menu needed (low page count).
- Brand mark left-aligned, theme toggle right-aligned.
- Background: `base-200` in light, `base-200` in dark. No strong color bar; a subtle shadow (`.app-navbar`) adds depth against the content.

### Cards / Panels
- Used sparingly for grouping related data (cost breakdown, decision variables).
- 1px border (`base-300`) with a subtle elevation shadow (`--pu-shadow`). Border-radius: 8px (`rounded-lg`).
- Hover state: deepened shadow (`--pu-shadow-lg`) plus a primary-tinted border (`oklch(var(--p) / 0.40)`), no layout motion. Apply via the shared `.panel` class.
- Header: semibold text, no background differentiation.

### Tables
- Zebra-striped rows for readability.
- Compact row height (py-2).
- Monospace font for all numeric cells.
- Right-aligned numbers, left-aligned text.
- Header row uses `text-xs uppercase tracking-wider` for formality.
- Row hover: each `<tbody>` row picks up a subtle primary-tinted background (`oklch(var(--p) / 0.07)`) on hover, signaling interactivity. No layout motion; transitions respect `prefers-reduced-motion: reduce`.

### Forms / Inputs
- DaisyUI `input-bordered` with `input-sm` sizing.
- Unit suffix displayed as inline badge or trailing text, not input-group addon.
- Validation: red border + inline error text on invalid.

### Buttons
- Primary: solid fill, used only for the main action (Otimizar).
- Secondary: ghost or outline for reset/navigation.
- Size: default for primary CTA, `btn-sm` for secondary actions.

### Alerts / Status Banners
- Full-width DaisyUI `alert` component.
- Icon + text, no dismiss button (status is permanent per page load).

### Collapsible Groups (Accordion)
- DaisyUI `collapse` with `collapse-arrow`.
- Grouped inside a vertical stack with 1px gap borders; the container carries a subtle shadow (`.panel-accordion`).
- Row highlight: the hovered title row gets a faint background tint (`oklch(var(--bc) / 0.05)`).
- First group open by default.

## Elevation & Interaction

Elevation is expressed through two theme-aware shadow tokens defined in `base.html`, tuned per theme (steel-blue tint in `winter`, deepened neutral in `business`):

| Token | Usage |
|-------|-------|
| `--pu-shadow` | Resting elevation for panels, the navbar, and the accordion container. |
| `--pu-shadow-lg` | Hover elevation for panels, paired with a primary-tinted border. |

Interaction stays understated: transitions run at 180–200 ms on an ease-out curve, with no translation or scale, and are fully disabled under `prefers-reduced-motion: reduce`.

## Dark Mode Implementation

Dark mode uses DaisyUI's native theme switching via the `data-theme` attribute on `<html>`. A toggle button in the navbar switches between `winter` (light) and `business` (dark). User preference is persisted to `localStorage` and respects `prefers-color-scheme` on first visit.

## Number Formatting (pt-BR)

All numeric values displayed to the user use Brazilian locale formatting:

| Format | Example Input | Example Output |
|--------|--------------|----------------|
| Decimal separator | `.` | `,` |
| Thousands separator | `,` | `.` |
| Example: 1000.85 | — | `1.000,85` |
| Example: 6176.7 | — | `6.176,7` |
| Signed slack: -0.0042 | — | `-0,0042` |

Implementation: custom Jinja2 filters `fmt_br(decimals)` and `fmt_br_signed(decimals)` registered in `app.py`. HTML form inputs retain standard numeric format (period decimal) for browser compatibility.

## Spacing Scale

| Context | Value |
|---------|-------|
| Page padding (horizontal) | `px-4 lg:px-8` |
| Section gap | `space-y-6` |
| Card internal padding | `p-5` |
| Form grid gap | `gap-4` |
| Table cell padding | `px-3 py-2` |

## Iconography

Lucide Icons via CDN (lightweight, consistent stroke width). Replaces Bootstrap Icons.
