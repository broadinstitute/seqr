import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import VariantGenes, { GeneDetails } from './VariantGene'

import {
  STATE1, GENE, VARIANT, MISSENSE_CONSTRAINED_GENE, LOF_CONSTRAINED_GENE, PLI_CONSTRAINED_GENE,
} from '../fixtures'

configure({ adapter: new Adapter() })

const GENE_CONSTRAINT_LINK = 'a[href="https://gnomad.broadinstitute.org/help/constraint"]'

const renderedText = gene => mount(<GeneDetails gene={gene} compact />).text().replace(/\s+/g, ' ')

const withConstraints = (gene, constraints) => ({ ...gene, constraints: { ...gene.constraints, ...constraints } })

const expectGeneConstraintLink = (gene) => {
  const wrapper = mount(<GeneDetails gene={gene} compact />)
  expect(wrapper.text()).toMatch(/\.\sSee\sGene Constraint\sfor more information\./)
  const link = wrapper.find(GENE_CONSTRAINT_LINK)
  expect(link.text()).toBe('Gene Constraint')
  expect(link.prop('target')).toBe('_blank')
  expect(link.prop('rel')).toBe('noreferrer')
}

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<VariantGenes store={store} gene={GENE} variant={VARIANT} />)
})

test('missense constraint details show the gene rank, z-score and constraint help', () => {
  const text = renderedText(MISSENSE_CONSTRAINED_GENE)

  expect(text).toContain(
    'This gene ranks 1348 among 20076 genes evaluated for missense constraint (Z-score: 4.137). Missense constraint measures the depletion of missense variants observed in a gene relative to the number expected under a statistical model that accounts for local sequence context and other mutational factors [Samocha et al., 2014]. A higher positive Z-score indicates stronger constraint, meaning fewer missense variants are observed than expected. This metric can be particularly useful for prioritizing genes associated with dominant disorders, especially when a large proportion of the protein is functionally constrained. See Gene Constraint for more information.',
  )
  expect(text).not.toContain('ExAC')
  expect(text).not.toContain('gnomAD v4.1.2')
  expectGeneConstraintLink(MISSENSE_CONSTRAINED_GENE)
  expect(renderedText(withConstraints(MISSENSE_CONSTRAINED_GENE, { totalGenes: 19000 }))).toContain(
    'This gene ranks 1348 among 19000 genes evaluated for missense constraint',
  )
})

test('LoF constraint details show for a louef under the gnomAD v4 cutoff of 0.45', () => {
  expect(renderedText(LOF_CONSTRAINED_GENE)).toContain(
    'This gene ranks as 2224 most intolerant of LoF mutations by louef and 2444 by pLi out of 20076 genes under study in gnomAD v4.1.2 (louef: 0.3995, pLi: 0.9995) Karczewski (2020). See Gene Constraint for more information.',
  )
  expectGeneConstraintLink(LOF_CONSTRAINED_GENE)
  expect(renderedText(withConstraints(LOF_CONSTRAINED_GENE, { pli: 0 }))).toContain(
    'This gene ranks as 2224 most intolerant of LoF mutations by louef out of 20076 genes under study in gnomAD v4.1.2 (louef: 0.3995) Karczewski (2020). See Gene Constraint for more information.',
  )

  expect(renderedText(withConstraints(LOF_CONSTRAINED_GENE, { louef: 0.449, pli: 0.9 }))).toContain('intolerant of LoF mutations')
  expect(renderedText(withConstraints(LOF_CONSTRAINED_GENE, { louef: 0.45, pli: 0.9 }))).not.toContain('intolerant of LoF mutations')
  expect(renderedText(MISSENSE_CONSTRAINED_GENE)).not.toContain('intolerant of LoF mutations')
})

test('LoF constraint details show for a pLI over 0.9', () => {
  expect(mount(<GeneDetails gene={PLI_CONSTRAINED_GENE} />).text()).toContain('LOF CONSTR')
  expect(renderedText(PLI_CONSTRAINED_GENE)).toContain(
    'This gene ranks as 4187 most intolerant of LoF mutations by louef and 3016 by pLi out of 20076 genes under study in gnomAD v4.1.2 (louef: 0.5234, pLi: 0.9621) Karczewski (2020). See Gene Constraint for more information.',
  )

  const overPliCutoff = withConstraints(PLI_CONSTRAINED_GENE, { pli: 0.901 })
  expect(mount(<GeneDetails gene={overPliCutoff} />).text()).toContain('LOF CONSTR')
  expect(renderedText(overPliCutoff)).toContain('intolerant of LoF mutations')

  const atPliCutoff = withConstraints(PLI_CONSTRAINED_GENE, { pli: 0.9 })
  expect(mount(<GeneDetails gene={atPliCutoff} />).text()).not.toContain('LOF CONSTR')
  expect(renderedText(atPliCutoff)).not.toContain('intolerant of LoF mutations')
})
