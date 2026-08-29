---
name: Sophisticated Command Light
colors:
  surface: '#FFFFFF'
  surface-dim: '#F3F4F6'
  surface-bright: '#FFFFFF'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f5'
  surface-container: '#edeeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#111827'
  on-surface-variant: '#4B5563'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#D1D5DB'
  outline-variant: '#E5E7EB'
  surface-tint: '#3755c3'
  primary: '#00288e'
  on-primary: '#ffffff'
  primary-container: '#1e40af'
  on-primary-container: '#a8b8ff'
  inverse-primary: '#b8c4ff'
  secondary: '#555f70'
  on-secondary: '#ffffff'
  secondary-container: '#d6e0f4'
  on-secondary-container: '#596374'
  tertiary: '#532a00'
  on-tertiary: '#ffffff'
  tertiary-container: '#743d00'
  on-tertiary-container: '#ffa85d'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dde1ff'
  primary-fixed-dim: '#b8c4ff'
  on-primary-fixed: '#001453'
  on-primary-fixed-variant: '#173bab'
  secondary-fixed: '#d9e3f7'
  secondary-fixed-dim: '#bdc7db'
  on-secondary-fixed: '#121c2a'
  on-secondary-fixed-variant: '#3d4757'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#ffb77d'
  on-tertiary-fixed: '#2f1500'
  on-tertiary-fixed-variant: '#6e3900'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
  deep-indigo: '#1E40AF'
  alert-gold: '#D97706'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
    letterSpacing: 0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: 0.01em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
    letterSpacing: 0.01em
  headline-sm:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Hanken Grotesk
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.03em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-margin: 32px
  gutter: 24px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style
This design system is a light-themed evolution of a high-stakes security environment, shifting from "The Silent Sentinel" to "The Lucid Controller." It maintains an aura of calm authority and expensive precision while prioritizing clarity and alertness. The brand personality remains professional and unobtrusive, but feels more transparent and accessible.

The aesthetic follows a **Minimalist** and **Corporate Modern** style. It utilizes a high-contrast white and light grey base to reduce visual fatigue in well-lit environments. The interface retains the visual language of luxury engineering through strict alignment, expansive whitespace, and a focus on high-density information architecture that feels surgical rather than cluttered.

## Colors
The palette transitions to a high-contrast, professional light mode centered around **Deep Indigo** accents.

- **Primary:** Deep Indigo (#1E40AF) is used for critical actions, active states, and focus indicators.
- **Secondary:** Slate Grey (#374151) provides a grounded contrast for secondary navigation and iconography.
- **Tertiary/Accent:** A refined Amber Gold (#D97706) is used for warnings or high-priority alerts, maintaining a premium look without relying on aggressive reds.
- **Neutrals:** The background uses a very light grey (#F9FAFB), while primary surfaces are pure white (#FFFFFF) to create a clear hierarchy of information layers.
- **Interactive States:** Hover states should involve a subtle shift to a cooler grey (#F3F4F6); active states utilize the Deep Indigo fill with white text.

## Typography
Typography is the cornerstone of the system's sophisticated feel. **Hanken Grotesk** is used for headlines and labels to provide a sharp, contemporary edge. **Inter** is reserved for body text and data tables to ensure maximum legibility.

Headlines should use generous tracking to evoke a sense of breathing room. Labels, particularly in navigation or status indicators, must be set in uppercase with increased tracking (0.05em) to distinguish functional metadata from narrative content.

## Layout & Spacing
The layout uses a **Fixed Grid** model to ensure structural consistency for mission-critical dashboards.

- **Desktop:** 12-column grid, 1440px max-width, with 24px gutters.
- **Margins:** 32px outer margins create a framed, instrument-like appearance.
- **Rhythm:** A strict 8px baseline grid is enforced. Vertical spacing between modules follows a 16/32/64px progression.
- **Density:** For data-heavy logs, row heights are condensed to 40px, but internal cell padding must remain generous to avoid a "cramped" feel.

## Elevation & Depth
In this light-themed system, hierarchy is conveyed through **Low-Contrast Outlines** and very subtle **Ambient Shadows**.

1. **Level 0 (Base):** Off-white (#F9FAFB). Used for the global canvas.
2. **Level 1 (Surface):** Pure white (#FFFFFF). Used for main content cards and navigation. These are defined by a 1px border (#E5E7EB) rather than heavy shadows.
3. **Level 2 (Raised):** Pure white with a soft, diffused shadow (Blur: 12px, Opacity: 0.05, Color: Indigo-tinted). Used for modals, dropdowns, and active tooltips.

The goal is a "flat plus" look where depth is felt through hairline borders and slight luminosity changes rather than traditional skeuomorphic shadows.

## Shapes
The shape language is disciplined and geometric. A **Soft (0.25rem)** roundedness is the standard, maintaining a professional and precise finish.

- **Inputs/Buttons:** 4px radius.
- **Cards/Panels:** 8px (0.5rem) radius.
- **Selection Indicators:** Use vertical 3px indigo bars on the left edge of active menu items instead of rounded capsules to reinforce the architectural grid.

## Components
- **Buttons:** Primary buttons use Deep Indigo with white text. Secondary buttons use a white fill with a 1px Slate Grey border and Slate text.
- **Input Fields:** Use a white background with a 1px Light Grey border. On focus, the border transitions to Deep Indigo with a 2px outer glow (10% indigo opacity).
- **Cards:** Cards are defined by a 1px border (#E5E7EB). Shadows are only applied when cards are draggable or interactive.
- **Chips/Status:** Use a 10% opacity background of the status color (e.g., light indigo or light gold) with a bold 2px vertical accent bar on the left edge.
- **Data Tables:** Use 1px horizontal dividers (#F3F4F6). Header rows use a light grey background (#F9FAFB) and `label-md` typography.
- **Specialized Component - "The Pulse":** A small circular status indicator. In light mode, it uses a soft indigo breath (opacity cycling from 30% to 100%) to indicate live activity without being distracting.