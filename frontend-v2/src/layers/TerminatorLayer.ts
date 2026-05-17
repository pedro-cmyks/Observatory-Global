import { PolygonLayer } from '@deck.gl/layers';

const DEG_TO_RAD = Math.PI / 180;

function getDayOfYear(date: Date): number {
    const start = new Date(date.getFullYear(), 0, 0);
    return Math.floor((date.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
}

/**
 * Calculate the night-side polygon offset by `lngOffsetDeg` degrees toward the day side.
 * Positive offset shrinks the night polygon (twilight band toward day side).
 */
export function calculateTerminatorPolygon(date: Date = new Date(), lngOffsetDeg = 0): number[][] {
    const dayOfYear = getDayOfYear(date);
    const declination = -23.45 * Math.cos((360 / 365) * (dayOfYear + 10) * DEG_TO_RAD);
    const utcHours = date.getUTCHours() + date.getUTCMinutes() / 60;
    const solarNoonLng = -((utcHours - 12) * 15);

    const terminatorLine: number[][] = [];

    for (let lat = -90; lat <= 90; lat += 2) {
        const latRad = lat * DEG_TO_RAD;
        const declRad = declination * DEG_TO_RAD;
        const cosH = -Math.tan(latRad) * Math.tan(declRad);

        let lng: number;
        if (cosH < -1) {
            lng = solarNoonLng + 180;
        } else if (cosH > 1) {
            lng = solarNoonLng;
        } else {
            const hourAngle = Math.acos(Math.max(-1, Math.min(1, cosH))) / DEG_TO_RAD;
            lng = solarNoonLng + hourAngle;
        }

        lng += lngOffsetDeg;
        while (lng > 180) lng -= 360;
        while (lng < -180) lng += 360;

        terminatorLine.push([lng, lat]);
    }

    const nightSide = solarNoonLng > 0 ? -180 : 180;
    const nightPolygon: number[][] = [...terminatorLine];
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

// Twilight bands: 5 semi-transparent layers shrinking from full night toward the day side.
// Each offset step ≈ 3.5° lng ≈ ~300km at equator, covering ~1800km total twilight zone.
const TWILIGHT_BANDS = [
    { offset: 0,    alpha: 0.52 },
    { offset: 3.5,  alpha: 0.28 },
    { offset: 7.0,  alpha: 0.14 },
    { offset: 10.5, alpha: 0.07 },
    { offset: 14.0, alpha: 0.03 },
];

export function createTerminatorLayer(options: TerminatorLayerOptions, date?: Date): PolygonLayer[] {
    if (!options.visible) return [];

    const now = date ?? new Date();
    const baseAlpha = options.opacity ?? 1.0;

    return TWILIGHT_BANDS.map(({ offset, alpha }) => {
        const polygon = calculateTerminatorPolygon(now, offset);
        const a = Math.floor(alpha * baseAlpha * 255);
        return new PolygonLayer({
            id: `terminator-layer-${offset}`,
            data: [{ polygon }],
            getPolygon: (d: { polygon: number[][] }) => d.polygon,
            getFillColor: [0, 8, 25, a],
            stroked: offset === 0,
            getLineColor: [80, 120, 180, 40],
            lineWidthMinPixels: 1,
            pickable: false,
        });
    });
}
