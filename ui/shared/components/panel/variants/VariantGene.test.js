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

const expectNewTabLink = (wrapper, selector, text) => {
  const link = wrapper.find(selector)
  expect(link.text().trim()).toBe(text)
  expect(link.prop('target')).toBe('_blank')
  expect(link.prop('rel')).toBe('noreferrer')
}

const expectGeneConstraintLink = (gene) => {
  const wrapper = mount(<GeneDetails gene={gene} compact />)
  expect(wrapper.text()).toMatch(/\.\sSee\sGene Constraint\sfor more information\./)
  expectNewTabLink(wrapper, GENE_CONSTRAINT_LINK, 'Gene Constraint')
}

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<VariantGenes store={store} gene={GENE} variant={VARIANT} />)
})

test('missense constraint details show the gene rank, z-score and constraint help', () => {
  const text = renderedText(MISSENSE_CONSTRAINED_GENE)

  expect(text).toContain(
    'This gene ranks as the 1,348th most constrained against missense variation among the 20,076 genes evaluated in gnomAD v4.1.2 (Z-score: 4.137). Missense constraint measures the depletion of missense variants observed in a gene relative to the number expected under a statistical model that accounts for local sequence context and other mutational factors [Samocha et al., 2014]. A higher positive Z-score indicates stronger constraint, meaning fewer missense variants are observed than expected. This metric can be particularly useful for prioritizing genes associated with dominant disorders, especially when a large proportion of the protein is functionally constrained. See Gene Constraint for more information.',
  )
  expect(text).not.toContain('ExAC')
  expect(mount(<GeneDetails gene={MISSENSE_CONSTRAINED_GENE} compact />).text()).toMatch(/4\.137\)\.\sMissense constraint/)
  expectGeneConstraintLink(MISSENSE_CONSTRAINED_GENE)
  expectNewTabLink(
    mount(<GeneDetails gene={MISSENSE_CONSTRAINED_GENE} compact />),
    'a[href="https://pmc.ncbi.nlm.nih.gov/articles/PMC4222185/"]',
    'Samocha et al., 2014',
  )
  expect(renderedText(withConstraints(MISSENSE_CONSTRAINED_GENE, { totalGenes: 19000 }))).toContain(
    'most constrained against missense variation among the 19,000 genes evaluated',
  )
})

test('constraint ranks read as ordinals', () => {
  [
    [0, '0th'], [1, '1st'], [2, '2nd'], [3, '3rd'], [4, '4th'], [11, '11th'], [12, '12th'], [13, '13th'],
    [21, '21st'], [22, '22nd'], [23, '23rd'], [101, '101st'], [111, '111th'], [1002, '1,002nd'],
  ].forEach(([rank, ordinal]) => {
    expect(renderedText(withConstraints(MISSENSE_CONSTRAINED_GENE, { misZRank: rank }))).toContain(
      `This gene ranks as the ${ordinal} most constrained against missense variation`,
    )
    expect(renderedText(withConstraints(LOF_CONSTRAINED_GENE, { louefRank: rank }))).toContain(
      `This gene ranks as the ${ordinal} most constrained against loss-of-function (LoF) mutations`,
    )
  })
})

test('LoF constraint details show for a louef under the gnomAD v4 cutoff of 0.45', () => {
  expect(renderedText(LOF_CONSTRAINED_GENE)).toContain(
    'This gene ranks as the 2,224th most constrained against loss-of-function (LoF) mutations by LOEUF among the 20,076 genes evaluated in gnomAD v4.1.2 (LOEUF: 0.3995; pLI: 0.9995) [Karczewski et al., 2020]. See Gene Constraint for more information.',
  )
  expectGeneConstraintLink(LOF_CONSTRAINED_GENE)
  expectNewTabLink(
    mount(<GeneDetails gene={LOF_CONSTRAINED_GENE} compact />),
    'a[href="https://pubmed.ncbi.nlm.nih.gov/32461654/"]',
    'Karczewski et al., 2020',
  )
  expect(renderedText(withConstraints(LOF_CONSTRAINED_GENE, { pli: 0 }))).toContain(
    'This gene ranks as the 2,224th most constrained against loss-of-function (LoF) mutations by LOEUF among the 20,076 genes evaluated in gnomAD v4.1.2 (LOEUF: 0.3995) [Karczewski et al., 2020]. See Gene Constraint for more information.',
  )

  expect(mount(<GeneDetails gene={LOF_CONSTRAINED_GENE} compact />).text()).toMatch(/2020\]\.\sSee/)
  expect(renderedText(withConstraints(LOF_CONSTRAINED_GENE, { totalGenes: 19000 }))).toContain(
    'by LOEUF among the 19,000 genes evaluated in gnomAD v4.1.2',
  )

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
