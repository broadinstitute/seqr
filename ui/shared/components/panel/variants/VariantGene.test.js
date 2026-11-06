import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import VariantGenes, { GeneDetails } from './VariantGene'

import { STATE1, GENE, VARIANT, MISSENSE_CONSTRAINED_GENE, LOF_CONSTRAINED_GENE } from '../fixtures'

configure({ adapter: new Adapter() })

const GENE_CONSTRAINT_LINK = 'a[href="https://gnomad.broadinstitute.org/help/constraint"]'

const renderedText = gene => mount(<GeneDetails gene={gene} compact />).text().replace(/\s+/g, ' ')

const withConstraints = (gene, constraints) => ({ ...gene, constraints: { ...gene.constraints, ...constraints } })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<VariantGenes store={store} gene={GENE} variant={VARIANT} />)
})

test('missense constraint details show the gene rank, z-score and constraint help', () => {
  const wrapper = mount(<GeneDetails gene={MISSENSE_CONSTRAINED_GENE} compact />)

  expect(wrapper.text().replace(/\s+/g, ' ')).toContain(
    'This gene ranks as the 1,349th most constrained against missense variation among the 20,076 genes evaluated in gnomAD v4.1.2 (Z-score: 4.137).',
  )
  expect(wrapper.find('a[href="https://pmc.ncbi.nlm.nih.gov/articles/PMC4222185/"]').text()).toEqual('Samocha et al., 2014')
  expect(wrapper.find(GENE_CONSTRAINT_LINK).text()).toEqual('Gene Constraint')
})

test('LoF constraint details show for a louef under the gnomAD v4 cutoff of 0.45', () => {
  const wrapper = mount(<GeneDetails gene={LOF_CONSTRAINED_GENE} compact />)

  expect(wrapper.text().replace(/\s+/g, ' ')).toContain(
    'This gene ranks as the 2,225th most constrained against loss-of-function (LoF) mutations by LOEUF among the 20,076 genes evaluated in gnomAD v4.1.2 (LOEUF: 0.3995; pLI: 0.9995) [Karczewski et al., 2020].',
  )
  expect(wrapper.find('a[href="https://pubmed.ncbi.nlm.nih.gov/32461654/"]').text().trim()).toEqual('Karczewski et al., 2020')
  expect(wrapper.find(GENE_CONSTRAINT_LINK).text()).toEqual('Gene Constraint')
  expect(renderedText(withConstraints(LOF_CONSTRAINED_GENE, { pli: 0 }))).toContain('(LOEUF: 0.3995) [Karczewski et al., 2020].')

  const badgeText = gene => mount(<GeneDetails gene={gene} />).text()
  expect(renderedText(withConstraints(LOF_CONSTRAINED_GENE, { louef: 0.449 }))).toContain('by LOEUF')
  expect(badgeText(withConstraints(LOF_CONSTRAINED_GENE, { louef: 0.449 }))).toContain('LOF CONSTR')
  expect(renderedText(withConstraints(LOF_CONSTRAINED_GENE, { louef: 0.45 }))).not.toContain('Loss of Function Constraint')
  expect(badgeText(withConstraints(LOF_CONSTRAINED_GENE, { louef: 0.45 }))).not.toContain('LOF CONSTR')
  expect(renderedText(withConstraints(LOF_CONSTRAINED_GENE, { louef: 0.5, pli: 0.9999 }))).not.toContain(
    'Loss of Function Constraint',
  )
  expect(badgeText(withConstraints(LOF_CONSTRAINED_GENE, { louef: 0.5, pli: 0.9999 }))).not.toContain('LOF CONSTR')
  expect(renderedText(MISSENSE_CONSTRAINED_GENE)).not.toContain('Loss of Function Constraint')
})
