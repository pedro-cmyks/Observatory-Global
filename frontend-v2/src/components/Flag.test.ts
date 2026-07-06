import { describe, it, expect } from 'vitest';
import { resolveFlagCode } from './Flag';

describe('resolveFlagCode', () => {
    it('resolves plain ISO alpha-2 codes (any case)', () => {
        expect(resolveFlagCode('VE')).toBe('ve');
        expect(resolveFlagCode('us')).toBe('us');
        expect(resolveFlagCode('Gb')).toBe('gb');
    });

    it('remaps GDELT/FIPS codes to ISO before resolving', () => {
        expect(resolveFlagCode('CH')).toBe('cn'); // GDELT China, not Switzerland
        expect(resolveFlagCode('UK')).toBe('gb');
        expect(resolveFlagCode('GZ')).toBe('ps'); // Gaza/Palestine
        expect(resolveFlagCode('KN')).toBe('kp'); // North Korea
        expect(resolveFlagCode('KS')).toBe('kr'); // South Korea
    });

    it('returns null for missing, malformed, or unsupported codes', () => {
        expect(resolveFlagCode(null)).toBeNull();
        expect(resolveFlagCode(undefined)).toBeNull();
        expect(resolveFlagCode('')).toBeNull();
        expect(resolveFlagCode('XYZ')).toBeNull();
        expect(resolveFlagCode('1')).toBeNull();
        expect(resolveFlagCode('zz')).toBeNull(); // 2-letter but no flag shipped
    });
});
