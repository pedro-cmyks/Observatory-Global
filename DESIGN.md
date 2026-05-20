---
name: Atlas Design System
description: Self-contained visual design system for a public narrative intelligence console, daily brief, and investigation workspace.
version: 1.0.0
tokens:
  colors:
    background:
      primary:
        type: color
        value: "#070d17"
        description: Deep navy application background.
      secondary:
        type: color
        value: "#0a1220"
        description: Secondary shell and command surface.
      tertiary:
        type: color
        value: "#0c182b"
        description: Dense panel surface and recessed controls.
      blackened:
        type: color
        value: "#05090e"
        description: Near-black lower-depth panel shade.
      editorial:
        type: color
        value: "#0c1017"
        description: Newspaper-style brief page background.
      overlay:
        type: color
        value: "rgba(7, 13, 23, 0.86)"
        description: Translucent app overlay.
      panelGradient:
        type: gradient
        value: "linear-gradient(180deg, rgba(12, 24, 43, 0.94) 0%, rgba(7, 13, 23, 0.91) 100%)"
        description: Default intelligence panel background.
      appGlow:
        type: gradient
        value: "radial-gradient(circle at 50% 0%, rgba(29, 158, 117, 0.12) 0%, transparent 42%), radial-gradient(circle at 100% 100%, rgba(29, 158, 117, 0.05) 0%, transparent 45%)"
        description: Subtle ambient emerald glow behind the console.
      workspaceGlow:
        type: gradient
        value: "radial-gradient(circle at 50% 45%, rgba(29, 158, 117, 0.08), transparent 36%)"
        description: Center-weighted glow for investigation canvas.
      gridLine:
        type: color
        value: "rgba(29, 158, 117, 0.035)"
        description: Workspace grid line color.
    text:
      primary:
        type: color
        value: "#e2e8f0"
        description: Main readable text.
      high:
        type: color
        value: "#f8fafc"
        description: High-emphasis headings and selected labels.
      secondary:
        type: color
        value: "rgba(226, 232, 240, 0.68)"
        description: Secondary body copy and low-priority labels.
      muted:
        type: color
        value: "rgba(226, 232, 240, 0.42)"
        description: Metadata, counters, and inactive controls.
      faint:
        type: color
        value: "#475569"
        description: Disabled labels and grid-adjacent copy.
      inverseOnAccent:
        type: color
        value: "#003827"
        description: Text on bright emerald controls.
      editorialBody:
        type: color
        value: "rgba(226, 232, 240, 0.85)"
        description: Italic newspaper analysis body copy.
    brand:
      emerald:
        type: color
        value: "#68dbae"
        description: Primary Atlas signal color.
      emeraldDeep:
        type: color
        value: "#1d9e75"
        description: Structural emerald used for borders, brief accents, and indexes.
      emeraldBright:
        type: color
        value: "#86f8c9"
        description: Hover glow and bright brand emphasis.
      green:
        type: color
        value: "#4ade80"
        description: Positive state and live confirmation.
      teal:
        type: color
        value: "#2dd4bf"
        description: Public attention and people-side labels.
      cyan:
        type: color
        value: "#38bdf8"
        description: Search, geography, and public attention links.
      blue:
        type: color
        value: "#60a5fa"
        description: Focused narrative thread and country emphasis.
      violet:
        type: color
        value: "#a78bfa"
        description: Person/entity chips and co-mentioned people.
      amber:
        type: color
        value: "#fbbf24"
        description: Neutral mood, bias disclaimer, notable severity.
      orange:
        type: color
        value: "#f97316"
        description: Elevated severity.
      red:
        type: color
        value: "#ef4444"
        description: Critical severity and crisis mode.
    border:
      subtle:
        type: color
        value: "rgba(29, 158, 117, 0.15)"
        description: Default structural panel border.
      medium:
        type: color
        value: "rgba(29, 158, 117, 0.28)"
        description: Tooltip and active-adjacent borders.
      strong:
        type: color
        value: "rgba(104, 219, 174, 0.50)"
        description: Strong emerald active border.
      whiteFaint:
        type: color
        value: "rgba(255, 255, 255, 0.08)"
        description: Secondary separators inside dense panels.
      whiteSubtle:
        type: color
        value: "rgba(255, 255, 255, 0.12)"
        description: Editorial brief and neutral controls.
      focusBlue:
        type: color
        value: "rgba(96, 165, 250, 0.30)"
        description: Country and thread focus border.
      personViolet:
        type: color
        value: "rgba(167, 139, 250, 0.28)"
        description: Entity/person chip border.
      warningAmber:
        type: color
        value: "rgba(245, 158, 11, 0.22)"
        description: Coverage disclaimer border.
      dangerRed:
        type: color
        value: "rgba(239, 68, 68, 0.30)"
        description: Crisis and destructive borders.
    sentiment:
      positive:
        type: color
        value: "#4ade80"
      neutral:
        type: color
        value: "#94a3b8"
      negative:
        type: color
        value: "#f87171"
      warning:
        type: color
        value: "#f59e0b"
    severity:
      normal:
        type: color
        value: "#94a3b8"
      notable:
        type: color
        value: "#fbbf24"
      elevated:
        type: color
        value: "#f97316"
      critical:
        type: color
        value: "#ef4444"
    data:
      theme:
        type: color
        value: "#34d399"
        description: Theme graph node and relationship color.
      country:
        type: color
        value: "#60a5fa"
        description: Country graph node and selected geography color.
      source:
        type: color
        value: "#f59e0b"
        description: Source graph node and source-driven evidence color.
      person:
        type: color
        value: "#a78bfa"
        description: Person/entity graph node color.
      signal:
        type: color
        value: "#f87171"
        description: Individual signal graph node and recent item marker.
      chokepoint:
        type: color
        value: "#22d3ee"
        description: Maritime or strategic chokepoint graph color.
      publicAttention:
        type: color
        value: "#2dd4bf"
        description: Search/Wikipedia/public attention evidence color.
  typography:
    families:
      display:
        type: fontFamily
        value: "Outfit, -apple-system, BlinkMacSystemFont, sans-serif"
        description: Brand, hero, and high-impact headings.
      sans:
        type: fontFamily
        value: "Plus Jakarta Sans, -apple-system, BlinkMacSystemFont, sans-serif"
        description: Main console UI and body copy.
      technical:
        type: fontFamily
        value: "Space Grotesk, SF Mono, monospace"
        description: Command labels, panel headers, metadata, and control text.
      mono:
        type: fontFamily
        value: "SF Mono, Fira Code, JetBrains Mono, ui-monospace, monospace"
        description: Numbers, counters, code-like metadata, and tabular values.
      editorial:
        type: fontFamily
        value: "Georgia, Times New Roman, serif"
        description: Daily brief masthead, analysis, and newspaper cards.
      materialSymbols:
        type: fontFamily
        value: "Material Symbols Outlined"
        description: Optional icon font for symbolic controls.
    weights:
      regular:
        type: fontWeight
        value: 400
      medium:
        type: fontWeight
        value: 500
      semibold:
        type: fontWeight
        value: 600
      bold:
        type: fontWeight
        value: 700
      black:
        type: fontWeight
        value: 900
    sizes:
      micro:
        type: dimension
        value: "9px"
        description: Dense metadata, tiny badges, and brief labels.
      control:
        type: dimension
        value: "10px"
        description: Command bar controls and uppercase HUD labels.
      label:
        type: dimension
        value: "11px"
        description: Technical labels and small descriptive text.
      caption:
        type: dimension
        value: "12px"
        description: Panel captions, helper copy, and compact feed metadata.
      bodySmall:
        type: dimension
        value: "13px"
        description: Dense feed rows and side-panel body text.
      body:
        type: dimension
        value: "14px"
        description: Default UI copy.
      bodyLarge:
        type: dimension
        value: "15px"
        description: Editorial lead and brand-sized command text.
      panelTitle:
        type: dimension
        value: "16px"
        description: Detail panel titles.
      metric:
        type: dimension
        value: "18px"
        description: Compact metric values.
      headline:
        type: dimension
        value: "24px"
        description: Side-panel country and section headings.
      display:
        type: dimension
        value: "48px"
        description: Landing display type.
      masthead:
        type: dimension
        value: "52px"
        description: Daily brief newspaper masthead.
    lineHeights:
      tight:
        type: number
        value: 1.1
      compact:
        type: number
        value: 1.3
      default:
        type: number
        value: 1.5
      readable:
        type: number
        value: 1.6
      editorial:
        type: number
        value: 1.75
    letterSpacing:
      none:
        type: dimension
        value: "0em"
      tightDisplay:
        type: dimension
        value: "-0.02em"
      label:
        type: dimension
        value: "0.06em"
      technical:
        type: dimension
        value: "0.08em"
      wide:
        type: dimension
        value: "0.12em"
      masthead:
        type: dimension
        value: "0.12em"
      editorialFlag:
        type: dimension
        value: "0.20em"
  spacing:
    scale:
      xxs:
        type: dimension
        value: "2px"
      xs:
        type: dimension
        value: "4px"
      sm:
        type: dimension
        value: "6px"
      md:
        type: dimension
        value: "8px"
      lg:
        type: dimension
        value: "10px"
      xl:
        type: dimension
        value: "12px"
      panel:
        type: dimension
        value: "14px"
      compactSection:
        type: dimension
        value: "16px"
      section:
        type: dimension
        value: "24px"
      gutter:
        type: dimension
        value: "40px"
      landingGutter:
        type: dimension
        value: "48px"
      landingSection:
        type: dimension
        value: "120px"
    layout:
      commandBarHeight:
        type: dimension
        value: "48px"
      panelGap:
        type: dimension
        value: "10px"
      panelPadding:
        type: dimension
        value: "14px"
      sidebarWidth:
        type: dimension
        value: "340px"
      workspaceLeftOffset:
        type: dimension
        value: "52px"
      workspaceRightOffset:
        type: dimension
        value: "24px"
      workspaceFilterRail:
        type: dimension
        value: "190px"
      workspaceNotesPanel:
        type: dimension
        value: "320px"
      maxConsoleWidth:
        type: dimension
        value: "1920px"
      minimumViewportWidth:
        type: dimension
        value: "320px"
  radii:
    none:
      type: dimension
      value: "0px"
    xs:
      type: dimension
      value: "2px"
    sm:
      type: dimension
      value: "3px"
    control:
      type: dimension
      value: "4px"
    input:
      type: dimension
      value: "6px"
    panel:
      type: dimension
      value: "6px"
    board:
      type: dimension
      value: "8px"
    card:
      type: dimension
      value: "8px"
    softCard:
      type: dimension
      value: "10px"
    pill:
      type: dimension
      value: "999px"
    circle:
      type: dimension
      value: "50%"
  borders:
    hairline:
      type: border
      value: "1px solid rgba(255, 255, 255, 0.08)"
    panel:
      type: border
      value: "1px solid rgba(29, 158, 117, 0.15)"
    active:
      type: border
      value: "1px solid rgba(104, 219, 174, 0.50)"
    editorialRule:
      type: border
      value: "2px solid rgba(226, 232, 240, 0.12)"
    attention:
      type: border
      value: "1px solid rgba(45, 212, 191, 0.22)"
    warning:
      type: border
      value: "1px solid rgba(245, 158, 11, 0.22)"
  shadows:
    commandBar:
      type: shadow
      value: "0 12px 32px rgba(0, 0, 0, 0.36)"
    panelDepth:
      type: shadow
      value: "0 16px 44px rgba(0, 0, 0, 0.42)"
    modalDepth:
      type: shadow
      value: "0 24px 70px rgba(0, 0, 0, 0.46)"
    tooltip:
      type: shadow
      value: "0 8px 24px rgba(0, 0, 0, 0.62)"
    sidebar:
      type: shadow
      value: "18px 0 42px rgba(0, 0, 0, 0.38)"
    emeraldGlow:
      type: shadow
      value: "0 0 22px rgba(29, 158, 117, 0.15)"
    emeraldHover:
      type: shadow
      value: "0 0 16px rgba(29, 158, 117, 0.14)"
    brandTextGlow:
      type: shadow
      value: "0 0 10px rgba(29, 158, 117, 0.42)"
    dangerPulse:
      type: shadow
      value: "0 0 0 4px rgba(239, 68, 68, 0)"
  opacity:
    disabled:
      type: number
      value: 0.38
    secondary:
      type: number
      value: 0.68
    overlay:
      type: number
      value: 0.86
    activePanel:
      type: number
      value: 0.94
    tooltip:
      type: number
      value: 0.97
  motion:
    durations:
      instant:
        type: duration
        value: "80ms"
      fast:
        type: duration
        value: "150ms"
      standard:
        type: duration
        value: "240ms"
      panel:
        type: duration
        value: "280ms"
      graph:
        type: duration
        value: "300ms"
      reveal:
        type: duration
        value: "600ms"
      hero:
        type: duration
        value: "800ms"
      pulse:
        type: duration
        value: "3000ms"
      radar:
        type: duration
        value: "5000ms"
    easing:
      standard:
        type: cubicBezier
        value: "cubic-bezier(0.4, 0, 0.2, 1)"
      emphasized:
        type: cubicBezier
        value: "cubic-bezier(0.16, 1, 0.3, 1)"
      pulse:
        type: cubicBezier
        value: "cubic-bezier(0.4, 0, 0.6, 1)"
      linear:
        type: cubicBezier
        value: "linear"
      easeOut:
        type: cubicBezier
        value: "ease-out"
    patterns:
      hoverLift:
        type: transition
        value: "transform 200ms ease, border-color 200ms ease, box-shadow 200ms ease"
      panelSlide:
        type: transition
        value: "transform 280ms cubic-bezier(0.4, 0, 0.2, 1), opacity 200ms ease"
      quickColor:
        type: transition
        value: "color 150ms ease, background 150ms ease, border-color 150ms ease"
      tooltipReveal:
        type: transition
        value: "opacity 80ms ease"
      signalEnter:
        type: transition
        value: "background 650ms ease-out, box-shadow 650ms ease-out"
  elevation:
    levels:
      flat:
        type: number
        value: 0
      command:
        type: number
        value: 100
      workspaceTab:
        type: number
        value: 140
      workspace:
        type: number
        value: 150
      tooltip:
        type: number
        value: 10000
  effects:
    blur:
      commandBar:
        type: blur
        value: "20px"
      overlay:
        type: blur
        value: "18px"
      badge:
        type: blur
        value: "12px"
    grid:
      workspace:
        type: dimension
        value: "36px"
        description: Grid cell size for investigation graph canvas.
    focusRing:
      emerald:
        type: shadow
        value: "0 0 0 1px rgba(104, 219, 174, 0.44), 0 0 16px rgba(29, 158, 117, 0.14)"
  components:
    commandBar:
      height:
        type: dimension
        value: "48px"
      background:
        type: color
        value: "rgba(7, 13, 23, 0.90)"
      paddingInline:
        type: dimension
        value: "16px"
      gap:
        type: dimension
        value: "12px"
    button:
      heightCompact:
        type: dimension
        value: "26px"
      heightDefault:
        type: dimension
        value: "32px"
      paddingCompact:
        type: dimension
        value: "4px 10px"
      paddingDefault:
        type: dimension
        value: "5px 10px"
    panel:
      radius:
        type: dimension
        value: "6px"
      padding:
        type: dimension
        value: "14px"
      headerHeight:
        type: dimension
        value: "36px"
    tooltip:
      maxWidth:
        type: dimension
        value: "240px"
      padding:
        type: dimension
        value: "6px 9px"
      fontSize:
        type: dimension
        value: "10px"
    map:
      background:
        type: color
        value: "#07111f"
      land:
        type: color
        value: "#132235"
      water:
        type: color
        value: "#050b14"
      selectedCountry:
        type: color
        value: "#1d9e75"
      focusedCountry:
        type: color
        value: "#60a5fa"
      heatHigh:
        type: color
        value: "#68dbae"
      signalPoint:
        type: color
        value: "#fbbf24"
    brief:
      mastheadSize:
        type: dimension
        value: "52px"
      contentMaxWidth:
        type: dimension
        value: "860px"
      pagePadding:
        type: dimension
        value: "40px"
      ruleOpacity:
        type: number
        value: 0.12
    workspace:
      shellRadius:
        type: dimension
        value: "8px"
      filterRailWidth:
        type: dimension
        value: "190px"
      notesWidth:
        type: dimension
        value: "320px"
      graphGridSize:
        type: dimension
        value: "36px"
      tabWidth:
        type: dimension
        value: "40px"
breakpoints:
  mobile:
    type: dimension
    value: "700px"
  tablet:
    type: dimension
    value: "980px"
  desktop:
    type: dimension
    value: "1200px"
  wide:
    type: dimension
    value: "1920px"
---

# Atlas Visual Identity

Atlas is a public narrative intelligence console. Its visual language should feel like a live analyst workstation: precise, dense, dark, and calm under pressure. The interface should communicate that it is processing open signals, public attention, geography, source provenance, and investigation memory in real time.

The brand is not a generic news dashboard and not a decorative AI product. It is a command surface for reading how public narratives move. The strongest visual signal is the contrast between near-black navy depth and emerald evidence light.

## Core Aesthetic

The product lives in an “intelligence dark mode.” Backgrounds are almost black but never flat black: deep navy layers, radial emerald glow, translucent panels, and thin borders create the sense of a radar room or operations console. Use restrained light, not neon overload.

The primary color is emerald. It represents signal, liveness, selection, and trustworthy action. Amber is used for caution, coverage bias, neutral mood, and notable attention. Blue and cyan are for geographic focus, search/public attention, and link-like pivots. Violet is reserved for people and entities. Red should remain scarce and meaningful: crisis, critical severity, destructive action, or strong negative sentiment.

## Product Surfaces

Atlas has three connected surfaces:

1. The landing page introduces Atlas as public narrative intelligence. It may be more editorial and spacious, but should still use the same dark navy, emerald signal glow, and technical labels.
2. The daily brief is the readable orientation layer. It deliberately borrows from newspapers: serif masthead, center-aligned stats, rules, italic analysis, country filters, and grid-like theme sections. It should feel legible and public-facing, not like a control room.
3. The app console is the analyst layer. It should be dense, HUD-like, and spatial. Map, stream, narrative threads, anomaly/public attention, source integrity, and workspace all share the same compact command language.

## Layout Principles

The console starts with a fixed 48px command bar. This bar is compact and utilitarian: brand, live data, global search, time controls, status stats, brief/workspace/tour/settings. Avoid tall navigation, marketing headers, or large empty hero space inside the app.

Panels should feel mounted to a tactical grid. Use small radii, one-pixel borders, subtle gradients, and compact padding. Layout should prioritize scan speed over decoration. Dense text is acceptable when hierarchy is clear.

The map is a primary surface, not a decorative background. It should look muted until selected geography or narrative activity lights it up. Heat should communicate baseline-normalized attention; raw volume should read as evidence density, not importance.

The workspace is an investigation board. It should feel like a separate but connected surface: fixed overlay, grid canvas, filter rail, graph stage, trail/pinned side panel, and export actions. Trail and pinned content should have distinct meaning: Trail is the chronological path of investigation; Pinned is curated evidence.

## Typography

Use Outfit for brand and major display moments. It should feel geometric and confident, never playful.

Use Plus Jakarta Sans for the working interface. It carries body copy, panel summaries, settings, and dense rows.

Use Space Grotesk and mono fallbacks for command labels, uppercase metadata, counters, badges, tabs, and timestamps. These labels should be small, uppercase, and letter-spaced.

Use Georgia only in the daily brief and editorial analysis moments. The serif voice signals “read this as a brief,” while the console sans/mono voice signals “interact and investigate.”

Numbers should use tabular treatment wherever possible. Counts, sentiment, source health, countries, wiki views, and timestamps should align visually and avoid jitter.

## Color Usage

Emerald should mark action, selected states, live status, primary CTAs, active time range, workspace focus, and structural accents. Do not flood every component with bright emerald; most borders should use low-opacity emerald.

Amber should be the caution language: bias disclaimers, limited confidence, notable alerts, neutral mood, and sentiment warnings.

Cyan and blue separate public attention and geography from general signal. Public Attention should often lean teal/cyan; country focus and narrative focus can use blue.

Violet is for people/entity chips and co-mentioned person networks. It should not become the main brand color.

Red should be reserved. It is not a general accent.

## Panels And Controls

Panel headers use uppercase technical labels with wide tracking. Header copy should be short and operational: “SIGNAL STREAM,” “NARRATIVE THREADS,” “ANOMALY ALERT,” “SOURCE INTEGRITY,” “PUBLIC ATTENTION.”

Buttons are compact rectangles with 3-6px radii. Active buttons may invert to emerald with deep green text. Secondary icon buttons stay translucent with thin borders. Pills are allowed for chips, counts, country filters, and small contextual labels.

Tooltips should appear instantly and feel native to the console: near-black background, emerald border, 10px sans text, compact padding, and high z-index.

Empty states should be quiet and explicit. Avoid large illustrations. Use small muted text that explains whether the current time window, country, or local data source is limiting the view.

## Data Visualization

Graphs, maps, and timelines should look like instruments. Prefer dark plotting areas, faint grid lines, glowing points, compact legends, and restrained color coding.

Narrative graphs should separate node types through color and relationship type, not through heavy card containers. Labels must remain readable. If a graph becomes dense, use force spacing, progressive reveal, filters, or labels-on-focus rather than allowing text to stack into an unreadable cluster.

Temporal charts should communicate movement first: drift, acceleration, fading, baseline deviation, and public/media divergence. Decorative chart chrome should stay minimal.

## Public Attention

Public Attention is the people-side evidence layer. It should feel related to Signal Stream but not identical to it. Media signals are what outlets publish; public attention is what people read, search, or notice.

Use teal/cyan accents for Public Attention. When an attention item opens a narrative, preserve its origin visually. The user should understand that the investigation moved from public interest into media evidence, not into an unrelated global topic.

## Brief Design

The brief should feel like a nighttime global newspaper. Its masthead is large, serif, uppercase, and letter-spaced. Stats are centered. Rules are thin and low-opacity. Analysis text is italic, serif, and bordered by emerald.

When filtered to a country, the map should dim the rest of the world and light the selected country. Country-specific stats, analysis copy, themes, and sources should update together. Theme cards should be large click targets that lead into the console with the country and narrative already selected.

## Motion

Motion should imply live processing. Use short transitions for controls, hover states, panel focus, and chip interactions. Use slower motion only for radar sweeps, signal pulses, reveal-on-scroll, or loading states.

Animations should never compete with analysis. A user should be able to read dense information while the interface is live.

## Accessibility And Density

This system accepts density but must preserve legibility. Text should not overlap controls, panels, graph labels, or map overlays. Small text is acceptable only where contrast and spacing make it readable.

Interactive elements should expose clear hover/focus states. Any icon-only control needs an accessible label or visible tooltip. Avoid native browser title tooltips; use the instant tooltip style described by the tokens.

## Implementation Guidance

Use the tokens above as literal values when recreating this visual system in another tool or generated UI. Do not substitute a bright cyberpunk palette, rounded SaaS cards, large pastel gradients, or marketing-page spacing inside the app console.

The system works best when it feels like a quiet command center: dark, editorial when needed, precise, and connected end to end from brief to console to workspace.
