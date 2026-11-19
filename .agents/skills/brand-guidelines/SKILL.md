---
name: brand-guidelines
description: Applies bahonavi's official brand colors, gradients, and typography to any artifact that may benefit from having bahonavi's look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply, including the GitLab Pulse React dashboard theme (frontend/src/styles/tokens.css, app/dashboard/palettes.py), SVG charts, docs diagrams, and screenshots.
---

# bahonavi Brand Styling

## Overview

bahonavi (*Back Home Navigation*) builds intelligent software, web applications, Python automation, and FPGA solutions. The visual identity bridges **technology and heritage** — modern, dark-first interfaces with warm brand accents that recall direction, guidance, and craftsmanship.

**Keywords**: branding, corporate identity, visual identity, styling, brand colors, typography, bahonavi brand, visual formatting, visual design, dark theme, light theme

---

## Where the brand lives in GitLab Pulse

UI chrome colors and fonts are CSS variables in the React frontend; semantic data colors are resolved in Python from YAML rule overrides and served to SVG charts:

| Brand token | GitLab Pulse location |
|---|---|
| `--bg`, `--bg-card`, `--bg-raise`, `--surface`, `--text`, `--heading`, `--muted`, `--accent`, `--brand`, `--grad` | `frontend/src/styles/tokens.css` under `:root` (dark default) and `[data-theme="light"]` |
| `--chart-1` ... `--chart-8` | `frontend/src/styles/tokens.css` (`:root` / `[data-theme="light"]`) |
| Semantic data colors (issue type, priority, severity, stage, milestone), light and dark | `_SEMANTIC_LIGHT` / `_SEMANTIC_DARK` + `resolve_palettes()` in `app/dashboard/palettes.py`, consumed in `frontend/src/lib/colors.ts` |
| Fonts | Self-hosted in `frontend/public/static/` (`Manrope`, `Space Grotesk`, `Space Mono`) and declared in `frontend/src/styles/fonts.css` |
| Logo, favicon | `frontend/public/static/logo.svg`, `frontend/public/static/favicon.png`, `docs/images/logo.svg` |

The dashboard defaults to dark mode in `frontend/src/App.tsx`; both modes must stay usable via the TopBar theme switcher. GitLab Pulse also uses **Space Mono** as the monospace font (`--font-mono`) for tabular counts, dates, and issue IDs.

---

## UI Color System

The website uses a token-based color system with a **dark theme (default)** and an optional **light theme**.

> **Source of truth:** the `:root` and `[data-theme='light']` blocks in the bahonavi website stylesheet (`website/assets/css/site.css` in the bahonavi repository). This skill mirrors them. When the two disagree, the stylesheet wins and this file is updated in every repository that carries a copy.

### Dark Theme (default)

| Token | Value | Role |
|---|---|---|
| `--bg` | `#050811` | Page background |
| `--bg-card` | `#0c1123` | Card / panel background |
| `--bg-raise` | `#111833` | Raised surface on top of a card (nested panels, popovers) |
| `--surface` | `rgba(255,255,255,0.05)` | Elevated surfaces (buttons, chips) |
| `--line` | `rgba(255,255,255,0.08)` | Borders and dividers |
| `--line-strong` | `rgba(255,255,255,0.16)` | Emphasized borders (secondary buttons, inputs) |
| `--text` | `#d4deee` | Primary body text (soft blue-white, reduced eye strain) |
| `--heading` | `#f3f6fc` | Headings and display text (brighter than body) |
| `--muted` | `#7a8fa8` | Secondary / muted text |
| `--accent` | `#00f2fe` | Highlight accent (cyan) |
| `--nav-bg` | `rgba(5,8,17,0.78)` | Navbar background (frosted glass) |
| `--shadow` | `0 20px 60px rgba(0,0,0,0.36)` | Card drop shadow |
| `--shadow-lg` | `0 40px 120px rgba(0,0,0,0.55)` | Featured elements (hero art, product shots) |

### Light Theme

| Token | Value | Role |
|---|---|---|
| `--bg` | `#e8ecf5` | Page background (blue-gray, more character) |
| `--bg-card` | `#f1f4fb` | Card / panel background |
| `--bg-raise` | `#f8faff` | Raised surface on top of a card |
| `--surface` | `rgba(0,0,0,0.05)` | Elevated surfaces (buttons, chips) |
| `--line` | `rgba(0,0,0,0.12)` | Borders and dividers |
| `--line-strong` | `rgba(0,0,0,0.22)` | Emphasized borders |
| `--text` | `#0d1120` | Primary body text |
| `--heading` | `#070a16` | Headings and display text |
| `--muted` | `#3d5370` | Secondary / muted text (deeper, more readable) |
| `--accent` | `#006ea3` | Highlight accent (richer cyan-blue) |
| `--nav-bg` | `rgba(232,236,245,0.86)` | Navbar background (frosted glass) |
| `--shadow` | `0 20px 60px rgba(13,17,32,0.12)` | Card drop shadow |
| `--shadow-lg` | `0 40px 120px rgba(13,17,32,0.2)` | Featured elements |

Set `color-scheme: dark` on `:root` and `color-scheme: light` on `[data-theme='light']` so native controls and scrollbars follow the theme.

---

## Brand Colors (shared across both themes)

| Token | Value | Role |
|---|---|---|
| `--brand` | `#ff512f` | Primary brand color (orange-red) |
| `--brand-2` | `#dd2476` | Secondary brand color (pink) |
| `--grad` | `linear-gradient(135deg, #ff512f → #dd2476)` | CTA buttons, step badges, dividers |
| `--button-text` | `#ffffff` | Text on the brand gradient |

> These colors and the gradient are **never overridden** by the light theme — they are always used the same way regardless of theme.

---

## Brand Gradient

The signature gradient is used on all primary calls-to-action, step-number badges, and process dividers.

```css
background: linear-gradient(135deg, #ff512f 0%, #dd2476 100%);
```

**Usage:** CTA buttons (`.btn-primary`), process step numbers, gradient text on headings (`.grad-text`), the reading-progress hairline under the navbar, and the single highlighted bar in a chart.

---

## Accent & Node Colors

Used in diagrams, SVG nodes, and decorative elements.

| Token | Dark | Light | Role |
|---|---|---|---|
| `--node-cyan` | `#4facfe` | `#005e9e` | Primary diagram node |
| `--node-pink` | `#f5576c` | `#b51c3c` | Secondary diagram node |
| `--node-purple` | `#da22ff` | `#8a0ea8` | Tertiary diagram node |
| `--gold` | `#ffa751` | `#b06000` | Warm highlight (ratings, awards, warm data marks) |
| `--star` | `#fff1c5` | `#fff1c5` | Star / spark highlight in the logomark |

### Code Sample Colors

For syntax-highlighted snippets shown as page content (not editor themes).

| Token | Dark | Light | Role |
|---|---|---|---|
| `--code-key` | `#74c7f0` | `#005e9e` | Keys, properties |
| `--code-value` | `#56d4b0` | `#1a7a62` | Values, strings |
| `--code-kw` | `#c76bff` | `#8a0ea8` | Keywords |

---

## Logo SVG Gradients

The bahonavi logomark uses four internal gradients that are **theme-independent**.

| ID | Direction | Color Stop 1 | Color Stop 2 |
|---|---|---|---|
| `nPG` — pillar | top → bottom | `#FF512F` | `#DD2476` |
| `nLG` — left arm | bottom-right → top-left | `#DA22FF` | `#9733EE` |
| `nRG` — right arm | bottom-left → top-right | `#F5576C` | `#F093FB` |
| `nOG` — orbit glow | left → right | `#00f2fe` (80%) → `#4facfe` (10%) → `#00f2fe` (60%) |

---

## Typography

| Role | Token | Font | Fallback | Weights |
|---|---|---|---|---|
| **Headings / Display** | `--font-display` | Space Grotesk | system-ui, sans-serif | 500, 700 |
| **Body Text** | `--font-body` | Manrope | system-ui, sans-serif | 400, 500, 700 |
| **Code / Technical labels** | `--font-mono` | ui-monospace, SFMono-Regular, Menlo, Consolas | monospace | 400, 700 |

### Typographic Rules

- Headings use **Space Grotesk** 700 in `--heading`, with tight letter-spacing (`−0.035em`; `−0.05em` for the hero headline) and line-height `1.02–1.12`.
- Body text uses **Manrope** in `--text` at `line-height: 1.6`.
- Section labels are uppercase Space Grotesk 700 at `0.76rem` with `letter-spacing: 0.18em`, in `--accent`.
- Brand name accents (e.g. nav chips) use `letter-spacing: 0.08em` uppercase.
- **Self-host the fonts** as variable `woff2` files with `font-display: swap`. Do not load them from Google Fonts or any other third party; bahonavi pages make no third-party requests.

---

## Layout & Shape Tokens

| Token | Value | Usage |
|---|---|---|
| `--r` | `20px` | Border radius for cards and panels |
| `--max` | `1180px` | Max content width |
| `--nav-height` | `76px` | Fixed navbar height; also the base for `scroll-padding-top` |
| `--ease` | `cubic-bezier(0.16, 1, 0.3, 1)` | Default easing for transforms and reveals |
| `--grid-opacity` | `0.28` dark / `0.5` light | Opacity of the blueprint grid background |
| Base font | `var(--font-body)` | Body default |
| Body line-height | `1.6` | Comfortable reading |

### Radius Scale

| Radius | Usage |
|---|---|
| `20px` (`--r`) | Cards, panels |
| `14px` | Buttons (`12px` for small buttons) |
| `12–13px` | Icon tiles, inner panels, inputs |
| `6–8px` | Small inner elements (KPI tiles, chart bars) |
| `999px` | Chips, kickers, pills |

---

## Signature Patterns

These recur on every bahonavi surface and are what makes separate products read as one family.

- **Page background:** `--bg` with two soft corner glows (`--node-purple` top-left, `--node-cyan` top-right, mixed at roughly 11–13% with transparent) and a fixed 72px blueprint grid drawn in `--line`, faded out toward the bottom with a mask and scaled by `--grid-opacity`. Never a flat solid background.
- **Section label:** the uppercase accent label, preceded by a 28px × 1px rule in the same color and optionally a muted, tabular-figure index.
- **Section head:** left-aligned, two columns: the headline on the left, a `--muted` paragraph on the right with a 2px `--accent` top border. Not centered.
- **Navbar:** transparent at the top of the page; on scroll it takes `--nav-bg` with `backdrop-filter: blur(18px) saturate(140%)` and a `--line` bottom border. The primary gradient CTA sits at its right edge.
- **Buttons:** primary uses `--grad` with `--button-text` and a brand-tinted glow; secondary uses `--surface` with a `--line-strong` border that turns `--accent` on hover. Both lift 2px on hover. One primary button per view.
- **Cards:** `--bg-card` with a `--line` border and `--r` radius. On hover the border shifts toward `--accent` and a faint accent spotlight follows the pointer. Only interactive cards get hover effects.
- **Chips and kickers:** pill shape, `--surface` background, `--line` border, small bold text.
- **Focus:** `:focus-visible` shows a 2px `--accent` outline with a 4px offset. Never remove outlines without this replacement.
- **Motion:** eased with `--ease`; reveal-on-scroll only when JavaScript is running; everything is disabled under `prefers-reduced-motion: reduce`.

---

## Color Application Principles

1. **Dark-first.** The default experience is dark (`#050811` background). Light theme is an opt-in alternative.
2. **Brand gradient for action.** The orange→pink gradient signals interactivity and importance. Reserve it for CTAs, key highlights, and step indicators. Do not use `--brand` as a generic fill for data, destructive actions, or tertiary links.
3. **Cyan accent for information.** `--accent` (cyan `#00f2fe` dark / `#006ea3` light) marks links, section labels, chips, and informational callouts.
4. **Muted for secondary content.** `--muted` grays carry supporting text, captions, and icon defaults. Use sparingly to preserve hierarchy.
5. **Headings are brighter than body.** Use `--heading` for display text and `--text` for paragraphs; the contrast step is part of the hierarchy.
