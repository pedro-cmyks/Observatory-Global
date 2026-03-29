/**
 * Color utilities for Deck.gl layers
 */

/**
 * Convert CSS hex color to RGBA array for Deck.gl
 */
export function hexToRgba(hex: string, alpha: number = 255): [number, number, number, number] {
    // Handle rgba() strings
    if (hex.startsWith('rgba(')) {
        const match = hex.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/)
        if (match) {
            return [
                parseInt(match[1]),
                parseInt(match[2]),
                parseInt(match[3]),
                match[4] ? Math.round(parseFloat(match[4]) * 255) : alpha
            ]
        }
    }

    // Handle rgb() strings
    if (hex.startsWith('rgb(')) {
        const match = hex.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/)
        if (match) {
            return [parseInt(match[1]), parseInt(match[2]), parseInt(match[3]), alpha]
        }
    }

    // Handle hex colors
    const cleanHex = hex.replace('#', '')
    const r = parseInt(cleanHex.substring(0, 2), 16)
    const g = parseInt(cleanHex.substring(2, 4), 16)
    const b = parseInt(cleanHex.substring(4, 6), 16)

    return [r, g, b, alpha]
}

/**
 * Calculate node radius with optional size boost
 * Uses log scale for better perception across data ranges
 */
export function calculateNodeRadius(signalCount: number, boosted: boolean = false): number {
    const count = signalCount || 0
    if (count <= 0) return 100  // Minimum visible

    // Log scale for better perception
    const base = Math.sqrt(count) * 150

    // 2.5x boost for very obvious effect
    return boosted ? base * 2.5 : base
}

/**
 * Get theme-aware arc colors for Deck.gl ArcLayer
 */
export function getThemedArcColors(
    themeId: string,
    strength: number,
    isFocusRelated: boolean = false,
    isMuted: boolean = false
): { source: [number, number, number, number]; target: [number, number, number, number] } {

    const baseOpacity = Math.floor(Math.min(255, (strength || 0.3) * 255 * 1.5))

    if (isMuted) {
        // Very dim for non-focus arcs
        return {
            source: [80, 80, 100, 40],
            target: [100, 80, 80, 40],
        }
    }

    if (isFocusRelated) {
        // Highlighted arcs - bright cyan to purple
        return {
            source: [56, 189, 248, 220],
            target: [168, 85, 247, 220],
        }
    }

    // Theme-specific colors for global view
    if (themeId === 'retro-radar') {
        // Green phosphor style
        return {
            source: [74, 222, 128, baseOpacity],  // Green
            target: [34, 211, 238, baseOpacity],  // Cyan
        }
    }

    // Intel Noir (default) - Muted steel blue
    return {
        source: [100, 140, 180, baseOpacity],  // Steel blue
        target: [140, 120, 160, baseOpacity],  // Muted lavender
    }
}

/**
 * Get narrative intensity colors based on Phase 1 Redesign Brief:
 * Red = spiking. Blue = quiet. Green = positive shift.
 */
export function getIntensityColor(
    anomalyMultiplier: number,
    sentiment: number
): [number, number, number, number] {
    // Spiking (Anomaly) -> Red
    if (anomalyMultiplier > 1.5) {
        return [239, 68, 68, 220] // Tailwind red-500
    }
    // Positive shift -> Green
    if (sentiment > 0.15) {
        return [34, 197, 94, 220] // Tailwind green-500
    }
    // Quiet / Default -> Blue
    return [56, 189, 248, 160] // Tailwind sky-400
}
