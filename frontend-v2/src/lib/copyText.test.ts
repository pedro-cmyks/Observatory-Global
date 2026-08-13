import { describe, it, expect, vi } from 'vitest'
import { copyText } from './copyText'

describe('copyText', () => {
  it('reports true only after the write actually resolved', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    await expect(copyText('a line', { writeText })).resolves.toBe(true)
    expect(writeText).toHaveBeenCalledWith('a line')
  })

  it('reports false when the clipboard rejects — never a silent success claim', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'))
    await expect(copyText('a line', { writeText })).resolves.toBe(false)
  })

  it('reports false when no clipboard API exists', async () => {
    await expect(copyText('a line', null)).resolves.toBe(false)
  })

  it('refuses to "copy" nothing', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    await expect(copyText('   ', { writeText })).resolves.toBe(false)
    expect(writeText).not.toHaveBeenCalled()
  })
})
