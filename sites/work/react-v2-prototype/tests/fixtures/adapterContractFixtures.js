export const validAdapterFixture = Object.freeze({
  degrees: Object.freeze([
    Object.freeze({
      id: 'level1',
      label: 'Degree 1',
      title: 'Entered Apprentice',
      summary: 'Synthetic degree summary for adapter contract tests.',
      tone: '#8c6a24',
      categories: Object.freeze([
        Object.freeze({ id: 'all', label: 'All' }),
        Object.freeze({ id: 'symbols', label: 'Symbols' })
      ])
    }),
    Object.freeze({
      id: 'library',
      label: 'Library',
      title: 'Sources and Archive',
      summary: 'Synthetic source surface.',
      tone: '#496f82',
      categories: Object.freeze([
        Object.freeze({ id: 'all', label: 'All' }),
        Object.freeze({ id: 'source_book', label: 'Books' })
      ])
    })
  ]),
  entries: Object.freeze([
    Object.freeze({
      degree: 'level1',
      title: 'Synthetic Topic',
      slug: 'synthetic-topic',
      category: 'symbols',
      categoryLabel: 'Symbols',
      type: 'topic',
      status: 'open',
      summary: 'A synthetic topic entry, not runtime content.',
      body: 'Synthetic body text for view-model contract tests.',
      source: 'Synthetic Source',
      related: Object.freeze(['Synthetic Neighbor'])
    }),
    Object.freeze({
      degree: 'library',
      title: 'Synthetic Source Record',
      slug: 'synthetic-source-record',
      category: 'source_book',
      categoryLabel: 'Books',
      type: 'book',
      status: 'source',
      summary: 'A synthetic source entry, not runtime content.',
      body: 'Synthetic source note for view-model contract tests.',
      source: 'Synthetic Library Root',
      sourceYear: '1900',
      sourceKind: 'Book',
      coverage: 'synthetic fixture coverage',
      related: Object.freeze(['Synthetic Topic'])
    })
  ])
});

export const missingRequiredFieldFixture = Object.freeze({
  degrees: Object.freeze([
    Object.freeze({
      id: 'level1',
      label: 'Degree 1',
      summary: 'Missing title by design.',
      tone: '#8c6a24',
      categories: Object.freeze([])
    })
  ]),
  entries: Object.freeze([
    Object.freeze({
      degree: 'level1',
      title: '',
      slug: 'missing-title-topic',
      category: 'symbols',
      categoryLabel: 'Symbols',
      type: 'topic',
      status: 'open',
      summary: 'Invalid synthetic topic.',
      body: 'Synthetic body.',
      source: 'Synthetic Source',
      related: Object.freeze([])
    })
  ])
});

export const duplicateRouteFixture = Object.freeze({
  degrees: validAdapterFixture.degrees,
  entries: Object.freeze([
    Object.freeze({
      ...validAdapterFixture.entries[0]
    }),
    Object.freeze({
      ...validAdapterFixture.entries[0],
      title: 'Duplicate Synthetic Topic'
    })
  ])
});
