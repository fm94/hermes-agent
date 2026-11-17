import { describe, expect, it } from 'vitest'

import { fuzzyRank } from './fuzzy'
import { modelSearchText } from './model-search-text'

describe('modelSearchText', () => {
  it('keeps ordinary model ids unchanged', () => {
    expect(modelSearchText('kmx-k2.6')).toBe('kmx-k2.6')
    expect(modelSearchText('glx-5.2')).toBe('glx-5.2')
  })
})

describe('model picker search with aliases', () => {
  const models = ['kmx-k2.6', 'kmx-k2.5', 'k3', 'kmx-for-coding']

  it('surfaces k3 when the user searches kmx', () => {
    const ranked = fuzzyRank(models, 'kmx', modelSearchText).map(r => r.item)
    expect(ranked).toContain('k3')
  })

  it('still finds k3 by its wire id', () => {
    const ranked = fuzzyRank(models, 'k3', modelSearchText).map(r => r.item)
    expect(ranked).toEqual(['k3'])
  })

  it('does not invent k3 for unrelated queries', () => {
    const ranked = fuzzyRank(models, 'glx', modelSearchText).map(r => r.item)
    expect(ranked).toEqual([])
  })

  it('surfaces the Ox Alpha preview slug when the user searches ox', () => {
    const zenModels = ['x-preview-f-free', 'gpt-5.6-sol', 'kmx-k3']
    const ranked = fuzzyRank(zenModels, 'ox', modelSearchText).map(r => r.item)
    expect(ranked).toContain('x-preview-f-free')
    const rankedFull = fuzzyRank(zenModels, 'ox-alpha', modelSearchText).map(r => r.item)
    expect(rankedFull).toContain('x-preview-f-free')
  })
})
