# Radar UI Design Proposal (V1)

## Core Philosophy
"Global Information Radar" - A professional, immersive dashboard. The map is the hero; controls are subtle, floating instruments.

## Layout Structure

### 1. The Viewport (Z-Index 0)
- **Full-screen Map**: Covers 100vw / 100vh.
- **Style**: Dark mode (Mapbox Dark v11), minimal labels.

### 2. The Header (Z-Index 10)
- **Position**: Top-Left (Floating).
- **Content**:
  - **Title**: "OBSERVATORY GLOBAL" (Bold, tracking-wide).
  - **Subtitle**: "Live Narrative Radar" (Small, accent color).
- **Style**: No background pill. Just clean text with a subtle text-shadow for readability over the map.

### 3. The Control Deck (Z-Index 10)
- **Position**: Bottom-Center (Floating).
- **Design**: A sleek, glassmorphism bar (frosted black/gray).
- **Modules**:
  1.  **Time Window**: Segmented control [1h | 6h | 12h | 24h].
  2.  **Separator**: Vertical line.
  3.  **Layers**: Icon-based toggles with tooltips (or small text labels).
      -   [Icon] Heatmap
      -   [Icon] Flows
      -   [Icon] Nodes
- **Why Bottom-Center?**: Keeps the top view clear for the globe curvature and feels like a cockpit/dashboard.

### 4. The Sidebar (Z-Index 20)
- **Position**: Slide-over from Right.
- **Trigger**: Click on a Node.
- **Content**: Detailed metrics for the selected country/narrative.

## Responsive Behavior
- **Desktop**: Controls at bottom-center.
- **Mobile**: Controls stack at bottom, sidebar covers full screen.

## Visual Style
- **Colors**:
  -   Background: Transparent/Blur.
  -   Accents: Cyan (Flows), Magenta (Heatmap), White (Text).
-   **Typography**: Inter or Roboto Mono for data.

## Implementation Plan
1.  **Fix Map**: Ensure Mapbox renders with valid token and CSS.
2.  **Scaffold Layout**: CSS Grid/Flexbox overlay on top of `RadarMap`.
3.  **Componentize**: `RadarHeader`, `ControlDeck`, `DetailPanel`.
