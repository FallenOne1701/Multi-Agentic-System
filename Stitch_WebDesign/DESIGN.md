---
name: Groww Ops Precision
colors:
  surface: '#fbf8ff'
  surface-dim: '#d7d8f1'
  surface-bright: '#fbf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f2ff'
  surface-container: '#ececff'
  surface-container-high: '#e5e6ff'
  surface-container-highest: '#dfe1fa'
  on-surface: '#171a2c'
  on-surface-variant: '#3c4a43'
  inverse-surface: '#2c2f42'
  inverse-on-surface: '#f0efff'
  outline: '#6c7a73'
  outline-variant: '#bbcac1'
  surface-tint: '#006c4f'
  primary: '#006c4f'
  on-primary: '#ffffff'
  primary-container: '#00b386'
  on-primary-container: '#003d2c'
  inverse-primary: '#50ddad'
  secondary: '#3247e2'
  on-secondary: '#ffffff'
  secondary-container: '#4f63fb'
  on-secondary-container: '#fffbff'
  tertiary: '#a23d35'
  on-tertiary: '#ffffff'
  tertiary-container: '#f27a6e'
  on-tertiary-container: '#691411'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#71fac8'
  primary-fixed-dim: '#50ddad'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513b'
  secondary-fixed: '#dfe0ff'
  secondary-fixed-dim: '#bcc2ff'
  on-secondary-fixed: '#000b62'
  on-secondary-fixed-variant: '#102bcd'
  tertiary-fixed: '#ffdad6'
  tertiary-fixed-dim: '#ffb4ab'
  on-tertiary-fixed: '#410002'
  on-tertiary-fixed-variant: '#822620'
  background: '#fbf8ff'
  on-background: '#171a2c'
  surface-variant: '#dfe1fa'
  surface-bg: '#F8FAFC'
  surface-panel: '#FFFFFF'
  text-primary: '#111827'
  text-secondary: '#4B5563'
  text-tertiary: '#6B7280'
  border-subtle: '#E2E8F0'
  border-strong: '#CBD5E1'
  state-pass-bg: '#ECFDF5'
  state-pass-border: '#A7F3D0'
  state-pass-text: '#065F46'
  state-pass-dot: '#00B386'
  state-warn-bg: '#FFFBEB'
  state-warn-border: '#FDE68A'
  state-warn-text: '#92400E'
  state-warn-dot: '#F59E0B'
  state-danger-bg: '#FEF2F2'
  state-danger-border: '#FECACA'
  state-danger-text: '#991B1B'
  state-danger-dot: '#E11D48'
  redaction-bg: '#1E293B'
  redaction-text: '#38BDF8'
typography:
  headline-lg:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-xs:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-code:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: -0.01em
  label-token:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system defines an internal operations and compliance workbench engineered for speed, accuracy, and rigorous regulatory adherence in fintech support. The visual language evokes institutional calm, high-efficiency throughput, and absolute clarity. Built around an aesthetic of engineered utility, it rejects decorative neon glow, soft neumorphic curves, or "card soup" fragmentation in favor of crisp panel division, data-dense layouts, and precise contrast ratios.

The design movement bridges Modern Corporate and Utilitarian Minimalism. High typographic clarity, deliberate surface tints, and strict state semantics support customer support representatives, compliance officers, and tier-2 escalation engineers processing sensitive records under heavy workloads.

## Colors

The palette establishes an authoritative, reliable hierarchy built on crisp daylight neutrals with clear functional signaling:

- **Primary (`#00B386`)**: Deep emerald green serving as the signature confirmation and core action anchor. Reserved for primary commits, active toggle states, resolution triggers, and clean audit validations.
- **Secondary (`#5367FF`)**: Technical indigo accent used exclusively for navigation highlights, active filters, system-level shortcuts, and external ticket linkage.
- **Neutrals (`#44475B`, `#111827`, `#F8FAFC`)**: Canvas base is anchored by `#F8FAFC`, avoiding bright glare during long monitor shifts. Text uses sharp charcoal tones (`#111827` for high priority, `#4B5563` for metadata).
- **Compliance & Triage Badges**:
  - *Pass / Safe*: Tinted mint backdrop (`#ECFDF5`) framed by `#A7F3D0` with `#065F46` text.
  - *Attention / Escalate*: Warm amber tint (`#FFFBEB`) with `#92400E` text.
  - *Fail / Flagged*: Controlled crimson alert (`#FEF2F2`) with `#991B1B` text.
- **Redaction / PII Masking**: Slate-navy solid blocks (`#1E293B`) carrying high-contrast cyan-monospaced identifiers (`#38BDF8`) for explicit, error-proof handling of sensitive identities (e.g., PAN, Aadhaar, Bank Details, Email).

## Typography

Typography prioritizes information density and horizontal compactness without sacrificing scan speed:

- **Headings (Geist)**: Modern, low-contrast, and strictly geometric. Kept compact (never exceeding 24px) to preserve viewport area for multi-column ticket views and timeline audits.
- **Body & Data Grid (Inter)**: Clean, utilitarian, and legible under high-density tables. Numerical figures across balances, order counts, and timestamps must always use `font-feature-settings: "tnum" 1` for tabular alignment.
- **Data Tokens & PII Redaction (JetBrains Mono)**: Reserved for transaction IDs, masked tokens (`[PAN]`, `[BANK_IFSC]`, `[EMAIL]`), internal system codes, and error trace lines.

## Layout & Spacing

This design system uses a strict 3-pane workbench architecture:
1. **Left Queue / Nav Rail**: 280px fixed width, optimized for keyboard traversal (ticket queue, filters, status indicators).
2. **Center Action Canvas**: Fluid pane containing the conversation timeline, composer, customer order trail, and live notes.
3. **Right Context Inspector**: 360px fixed width displaying user KYC parameters, holdings snapshot, regulatory status, and compliance risk flags.

Horizontal rules and hairline panel borders replace floating card layouts. Layout components snap along a dense 4px/8px modular rhythm, prioritizing visible information per screen fold over decorative whitespace. On desktop viewpoints (<1440px), the right inspector collapses into an overlay toggle.

## Elevation & Depth

To maximize cognitive focus and eliminate distraction, depth is handled primarily through planar borders and tonal surfaces rather than heavy blur shadows:

- **Base Surfaces**: The main window uses `#F8FAFC`, while working panels utilize `#FFFFFF`.
- **Low-Contrast Outlines**: Panels, dividers, and tables are defined by 1px solid hairline borders (`#E2E8F0`). High-priority focus areas shift to `#CBD5E1`.
- **Floating Controls (Modals & Flyouts)**: Dropdown menus, typeaheads, and quick-reply overlays use a tight, non-diffused elevation: `0 4px 12px rgba(15, 23, 42, 0.08)`, edged with a 1px border (`#E2E8F0`).
- **Active Focus Ring**: Interactive inputs take a direct dual-layer focus outline: `0 0 0 1px #00B386, 0 0 0 3px rgba(0, 179, 134, 0.15)`.

## Shapes

Shapes reflect precision and restraint. The base border-radius is set to Soft (`0.25rem` / `4px`), ensuring buttons, input fields, and compliance tags sit compactly side-by-side without bulging corners or wasting tabular space. 

Badges and redaction tokens leverage a strict 3px to 4px radius to feel like machine-stamped data points rather than pill-shaped consumer tags. Modal sheets and dropdown panels use `rounded-lg` (`0.5rem` / `8px`).

## Components

### Buttons
- **Primary Action (Send / Resolve)**: Solid `#00B386` background, `#FFFFFF` text, `font-weight: 500`. Hover shifts to `#009E77`. Active state slightly darkened (`#008765`).
- **Secondary (Escalate / Flag)**: Transparent background with a 1px `#E2E8F0` border and `#111827` text. Hover uses `#F1F5F9`.
- **Danger (Reject / Lock Account)**: Outlined `#FECACA` border with `#991B1B` text. Hover transitions to `#FEF2F2`.

### Inputs & Composer Fields
- Crisp single-line text inputs and multi-line markdown reply boxes with 1px border in `#E2E8F0`. Padding uses `space-sm` vertically, `space-md` horizontally.
- Redaction syntax auto-highlights: typing placeholders like `[PAN]` formats into an inline token badge automatically.

### Status Badges & Chips
- Status indicators feature an 8px leading solid dot coupled with uppercase 11px label text.
- Padding is compact (`2px 8px`). Borders match state guidelines (`1px solid`).

### Compliance & Redaction Tokens
- Displayed with JetBrains Mono, uppercase styling (`[AADHAAR_XXXX]`, `[PAN_XXXX]`).
- Dark background (`#1E293B`) with cyan text (`#38BDF8`), featuring a click-to-reveal authorization flow with an audit log hook.

### Lists & Activity Logs
- Dense tabular rows with 36px to 40px row height.
- Alternating subtle hover states (`#F8FAFC`). No heavy borders separating inner rows; hairline `#F1F5F9` dividers only. Monospaced timestamps on the left margin.