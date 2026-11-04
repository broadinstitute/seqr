import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import VariantGenes, { GeneDetails } from './VariantGene'

import { STATE1, GENE, VARIANT, MISSENSE_CONSTRAINED_GENE, LOF_CONSTRAINED_GENE } from '../fixtures'

configure({ adapter: new Adapter() })

const renderedText = gene => mount(<GeneDetails gene={gene} compact />).text().replace(/\s+/g, ' ')

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<VariantGenes store={store} gene={GENE} variant={VARIANT} />)
})

test('missense constraint details name gnomAD v4.1.2', () => {
  const text = renderedText(MISSENSE_CONSTRAINED_GENE)

  expect(text).toContain('This gene ranks 1348 most constrained out of 20076 genes under study in terms of missense constraint (z-score: 4.137)')
  expect(text).toContain('Missense constraint is a measure of the degree to which the number of missense variants found in this gene in gnomAD v4.1.2 is higher or lower than expected')
  expect(text).not.toContain('ExAC')
  expect(text).not.toContain('Samocha')
})

test('LoF constraint details show for a louef under the gnomAD v4 cutoff of 0.45', () => {
  expect(renderedText(LOF_CONSTRAINED_GENE)).toContain(
    'This gene ranks as 2224 most intolerant of LoF mutations out of 20076 genes under study in gnomAD v4.1.2 (louef: 0.3995, pLi: 0.9995) Karczewski (2020)',
  )

  const withLouef = louef => ({ ...LOF_CONSTRAINED_GENE, constraints: { ...LOF_CONSTRAINED_GENE.constraints, louef } })
  expect(renderedText(withLouef(0.449))).toContain('intolerant of LoF mutations')
  expect(renderedText(withLouef(0.45))).not.toContain('intolerant of LoF mutations')
  expect(renderedText(MISSENSE_CONSTRAINED_GENE)).not.toContain('intolerant of LoF mutations')
})
