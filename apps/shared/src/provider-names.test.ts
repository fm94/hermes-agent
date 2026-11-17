import { describe, expect, it } from 'vitest'

import { providerDisplayNames } from './provider-names'

describe('providerDisplayNames', () => {
  it('returns bare names when all are unique', () => {
    expect(
      providerDisplayNames([
        { name: 'Anthropic', slug: 'anthropic' },
        { name: 'OpenAI', slug: 'openai' }
      ])
    ).toEqual(['Anthropic', 'OpenAI'])
  })

  it('appends slug to every collision so the disambiguation is symmetric', () => {
    expect(
      providerDisplayNames([
        { name: 'Kmx For Coding', slug: 'kmx-coding' },
        { name: 'Kmx For Coding', slug: 'kmx-coding-cn' }
      ])
    ).toEqual(['Kmx For Coding (kmx-coding)', 'Kmx For Coding (kmx-coding-cn)'])
  })

  it('only disambiguates the colliding group', () => {
    expect(
      providerDisplayNames([
        { name: 'Anthropic', slug: 'anthropic' },
        { name: 'Foo', slug: 'foo-a' },
        { name: 'Foo', slug: 'foo-b' }
      ])
    ).toEqual(['Anthropic', 'Foo (foo-a)', 'Foo (foo-b)'])
  })

  it('falls back to plain name if slug is empty', () => {
    expect(
      providerDisplayNames([
        { name: 'Foo', slug: '' },
        { name: 'Foo', slug: '' }
      ])
    ).toEqual(['Foo', 'Foo'])
  })

  it('skips disambiguation when slug equals name', () => {
    expect(
      providerDisplayNames([
        { name: 'foo', slug: 'foo' },
        { name: 'foo', slug: 'foo' }
      ])
    ).toEqual(['foo', 'foo'])
  })

  it('handles empty input', () => {
    expect(providerDisplayNames([])).toEqual([])
  })
})
