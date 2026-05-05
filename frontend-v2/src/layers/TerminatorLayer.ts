import { PolygonLayer } from '@deck.gl/layers';

const DEG_TO_RAD = Math.PI / 180;

function getDayOfYear(date: Date): number {
    const start = new Date(date.getFullYear(), 0, 0);
    return Math.floor((date.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
}

/**
 * Calculate the solar terminator (day/night boundary) polygon.
 * Returns coordinates for the "night side" of Earth.
 */
export function calculateTerminatorPolygon(date: Date = new Date()): number[][] {
    const dayOfYear = getDayOfYear(date);

    // Solar declination (angle of sun relative to equator)
    const declination = -23.45 * Math.cos((360 / 365) * (dayOfYear + 10) * DEG_TO_RAD);

    // Hour angle of subsolar point
    const utcHours = date.getUTCHours() + date.getUTCMinutes() / 60;
    const solarNoonLng = -((utcHours - 12) * 15);

    // Generate terminator line points
    const terminatorLine: number[][] = [];

    for (let lat = -90; lat <= 90; lat += 2) {
        const latRad = lat * DEG_TO_RAD;
        const declRad = declination * DEG_TO_RAD;

        // Hour angle where sun is at horizon
        const cosH = -Math.tan(latRad) * Math.tan(declRad);

        let lng: number;
        if (cosH < -1) {
            // Polar day
            lng = solarNoonLng + 180;
        } else if (cosH > 1) {
            // Polar night
            lng = solarNoonLng;
        } else {
            const hourAngle = Math.acos(Math.max(-1, Math.min(1, cosH))) / DEG_TO_RAD;
            lng = solarNoonLng + hourAngle;
        }

        while (lng > 180) lng -= 360;
        while (lng < -180) lng += 360;

        terminatorLine.push([lng, lat]);
    }

    // Close polygon on night side
    const nightPolygon: number[][] = [...terminatorLine];
    const nightSide = solarNoonLng > 0 ? -180 : 180;

    nightPolygon.push([nightSide, 90]);
    nightPolygon.push([nightSide, -90]);
    nightPolygon.push(terminatorLine[0]);

    return nightPolygon;
}

interface TerminatorLayerOptions {
    visible: boolean;
    opacity?: number;
    fillColor?: [number, number, number, number];
}

export function createTerminatorLayer(options: TerminatorLayerOptions, date?: Date): PolygonLayer | null {
    if (!options.visible) return null;

    const polygon = calculateTerminatorPolygon(date);
    const opacity = options.opacity ?? 0.4;
    const fillColor = options.fillColor ?? [0, 8, 25, Math.floor(opacity * 255)];

    return new PolygonLayer({
        id: 'terminator-layer',
        data: [{ polygon }],
        getPolygon: (d: { polygon: number[][] }) => d.polygon,
        getFillColor: fillColor,
        stroked: true,
        getLineColor: [80, 120, 180, 60],
        lineWidthMinPixels: 1,
        pickable: false,
    });
}
