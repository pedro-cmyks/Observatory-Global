import { describe, it, expect } from 'vitest';
import { resolveFlagCode } from './Flag';

describe('resolveFlagCode', () => {
    it('resolves plain ISO alpha-2 codes (any case)', () => {
        expect(resolveFlagCode('VE')).toBe('ve');
        expect(resolveFlagCode('us')).toBe('us');
        expect(resolveFlagCode('Gb')).toBe('gb');
    });

    it('is ISO-FIRST on collision codes (item-1 fix: CH is Switzerland, not FIPS China)', () => {
        expect(resolveFlagCode('CH')).toBe('ch'); // ISO Switzerland
        expect(resolveFlagCode('CN')).toBe('cn'); // ISO China
        expect(resolveFlagCode('BN')).toBe('bn'); // ISO Brunei, not FIPS Benin
        expect(resolveFlagCode('KN')).toBe('kn'); // ISO Saint Kitts, not FIPS North Korea
    });

    it('remaps legacy GDELT codes with no ISO meaning', () => {
        expect(resolveFlagCode('UK')).toBe('gb');
        expect(resolveFlagCode('GZ')).toBe('ps'); // Gaza/Palestine
        expect(resolveFlagCode('KS')).toBe('kr'); // South Korea
        expect(resolveFlagCode('RB')).toBe('rs'); // Serbia
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
