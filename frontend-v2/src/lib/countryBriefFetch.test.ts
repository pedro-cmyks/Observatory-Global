import { describe, expect, it } from 'vitest'
import { optionalFetchResponse } from './countryBriefFetch'

describe('CountryBrief optional fetches', () => {
  it('turns auxiliary fetch failures into null so the country brief can still render', async () => {
    const response = await optionalFetchResponse(() => Promise.reject(new Error('network down')))

    expect(response).toBeNull()
  })
})
