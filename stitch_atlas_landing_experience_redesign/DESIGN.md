---
title: Observatory Global Design System
description: Visual identity and design tokens for the Atlas narrative intelligence
  platform.
tokens:
  colors:
    background:
      primary: '#070d17'
      surface: '#0c182b'
      overlay: rgba(7, 13, 23, 0.85)
    brand:
      emerald: '#1D9E75'
      highlight: '#4ade80'
      glow: rgba(29, 158, 117, 0.12)
    text:
      primary: '#e2e8f0'
      secondary: rgba(226, 232, 240, 0.55)
      accent: '#1D9E75'
    border:
      subtle: rgba(29, 158, 117, 0.15)
      active: '#1D9E75'
  typography:
    families:
      display: Outfit, sans-serif
      body: Plus Jakarta Sans, sans-serif
      technical: Space Grotesk, monospace
      mono: SF Mono, Fira Code, monospace
    weights:
      regular: 400
      medium: 500
      semibold: 600
      bold: 700
    sizes:
      eyebrow: 11px
      body: 14px
      headline: 48px
      nav: 13px
  spacing:
    section: 120px
    gutter: 48px
    component: 24px
    inline: 12px
  radii:
    button: 4px
    card: 6px
  motion:
    standard: 0.3s cubic-bezier(0.4, 0, 0.2, 1)
    fast: 0.2s ease
    slow: 0.8s linear
  shadows:
    glow: 0 0 20px rgba(29, 158, 117, 0.15)
    depth: 0 10px 30px -10px rgba(0,0,0,0.5)
name: Observatory Global (Atlas) Design System
colors:
  surface: '#0f1512'
  surface-dim: '#0f1512'
  surface-bright: '#343b37'
  surface-container-lowest: '#0a0f0d'
  surface-container-low: '#171d1a'
  surface-container: '#1b211e'
  surface-container-high: '#252b28'
  surface-container-highest: '#303633'
  on-surface: '#dee4de'
  on-surface-variant: '#bccac1'
  inverse-surface: '#dee4de'
  inverse-on-surface: '#2c322e'
  outline: '#87948c'
  outline-variant: '#3d4943'
  surface-tint: '#68dbae'
  primary: '#68dbae'
  on-primary: '#003827'
  primary-container: '#26a37a'
  on-primary-container: '#003121'
  inverse-primary: '#006c4e'
  secondary: '#4de082'
  on-secondary: '#003919'
  secondary-container: '#00b55d'
  on-secondary-container: '#003e1c'
  tertiary: '#ffb3ad'
  on-tertiary: '#5f1413'
  tertiary-container: '#db726b'
  on-tertiary-container: '#560d0e'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#86f8c9'
  primary-fixed-dim: '#68dbae'
  on-primary-fixed: '#002115'
  on-primary-fixed-variant: '#00513a'
  secondary-fixed: '#6dfe9c'
  secondary-fixed-dim: '#4de082'
  on-secondary-fixed: '#00210c'
  on-secondary-fixed-variant: '#005227'
  tertiary-fixed: '#ffdad6'
  tertiary-fixed-dim: '#ffb3ad'
  on-tertiary-fixed: '#410003'
  on-tertiary-fixed-variant: '#7e2a27'
  background: '#0f1512'
  on-background: '#dee4de'
  surface-variant: '#303633'
  bg-primary: '#070d17'
  bg-surface: '#0c182b'
  bg-overlay: rgba(7, 13, 23, 0.85)
  text-primary: '#e2e8f0'
  text-secondary: rgba(226, 232, 240, 0.55)
  emerald-glow: rgba(29, 158, 117, 0.12)
  border-subtle: rgba(29, 158, 117, 0.15)
  border-active: '#1D9E75'
typography:
  display-xl:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-main:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  body-strong:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.6'
  nav-link:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1'
  technical-label:
    fontFamily: Space Grotesk
    fontSize: 11px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.08em
  code-snippet:
    fontFamily: SF Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.5'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  section: 120px
  gutter: 48px
  component: 24px
  inline: 12px
  stack-sm: 8px
  stack-xs: 4px
---

# Visual Identity & Design Intent

Observatory Global (Atlas) is a high-fidelity narrative intelligence platform. Its design system is built to convey **authority, precision, and global situational awareness**. It avoids traditional "news reader" aesthetics in favor of a sophisticated "command center" feel.

## Atmospheric Depth
The platform uses a deep, multi-layered background system. A dark slate primary background (`#070d17`) is accented with subtle radial gradients and glassmorphism to create a sense of three-dimensional space. This "Intelligence Dark Mode" reduces cognitive load while making high-contrast data visualizations pop.

## The Emerald Grid
Emerald green (`#1D9E75`) is the primary signature color. It represents "Signal" amidst the noise. 
- **Active States:** Used for borders, icons, and primary CTAs.
- **Data Glow:** Components often emit a subtle emerald glow (`0 0 20px`), simulating a technical projection or a radar screen.
- **Wireframes:** Structural elements use low-opacity emerald borders to maintain a "blueprint" or "tactical" aesthetic.

## Functional Typography
Three distinct typefaces manage the information hierarchy:
1. **Outfit:** Used for major headlines and brand statements. It is bold, modern, and high-impact.
2. **Plus Jakarta Sans:** The workhorse for data feeds and long-form analysis. It provides exceptional legibility at small sizes.
3. **Space Grotesk:** Reserved for "eyebrows," technical labels, and metadata. Its monospace-inspired geometry reinforces the platform's analytical nature.

## Motion as Intelligence
Animations are not decorative; they simulate active data processing.
- **The Radar Sweep:** A signature 360-degree scan line that "refreshes" data visualizations.
- **Orbital Paths:** Smooth, constant elliptical motions that suggest global continuity and "The World in Motion."
- **Pulsing Nodes:** Subtle opacity shifts that draw attention to new anomalies or critical signals without being disruptive.

## Layout & Structure
The layout prioritizes **Information Density** without clutter.
- **Glassmorphism:** Navigation and panels use background blurs (`blur(16px)`) to maintain context of the underlying map or globe.
- **Minimalist UI:** Buttons and inputs use thin borders and no heavy shadows, maintaining a lightweight, high-tech "heads-up display" (HUD) feel.