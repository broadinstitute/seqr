import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import VariantGenes, { GeneDetails, VariantGene } from './VariantGene'
import { BehindModalPopup } from '../../PopupWithModal'

import {
  STATE1, GENE, VARIANT, MISSENSE_CONSTRAINED_GENE, LOF_CONSTRAINED_GENE, CONSTRAINT_TRANSCRIPTS_BY_ID,
  NON_PREFERRED_TRANSCRIPT_VARIANT, SV_VARIANT_WITH_CONSTRAINED_GENES,
} from '../fixtures'

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
  expect(badgeText(withConstraints(LOF_CONSTRAINED_GENE, { louef: null }))).not.toContain('LOF CONSTR')
})

test('variant rows show constraints only for the main gene, from its main transcript', () => {
  const OVERLAPPING_GENE = {
    ...LOF_CONSTRAINED_GENE, cnSensitivity: { phi: 0.99, pts: 0.99 }, sHet: { postMean: 0.5 },
  }
  const store = configureStore()({
    ...STATE1,
    genesById: {
      [MISSENSE_CONSTRAINED_GENE.geneId]: MISSENSE_CONSTRAINED_GENE,
      [OVERLAPPING_GENE.geneId]: OVERLAPPING_GENE,
    },
    transcriptsById: CONSTRAINT_TRANSCRIPTS_BY_ID,
    modal: {},
  })
  const mountVariantGene = (geneId, variant, props) => mount(
    <Provider store={store}>
      <VariantGene geneId={geneId} variant={variant} compact {...props} />
    </Provider>,
  )
  const detailsText = (geneId, variant) => mount(
    mountVariantGene(geneId, variant).find(BehindModalPopup).prop('content'),
  ).text().replace(/\s+/g, ' ')
  const badgeText = (geneId, variant) => mountVariantGene(geneId, variant, { showInlineDetails: true }).text()
  const missenseGeneId = MISSENSE_CONSTRAINED_GENE.geneId
  const overlappingGeneId = OVERLAPPING_GENE.geneId

  const missenseText = detailsText(missenseGeneId, NON_PREFERRED_TRANSCRIPT_VARIANT)
  expect(missenseText).toContain(
    'This transcript ranks as the 3,201st most constrained against missense variation among the 20,076 genes evaluated in gnomAD v4.1.2 (Z-score: 3.500).',
  )
  expect(missenseText).not.toContain('Loss of Function Constraint')
  expect(badgeText(missenseGeneId, NON_PREFERRED_TRANSCRIPT_VARIANT)).toContain('MISSENSE CONSTR')
  expect(badgeText(missenseGeneId, NON_PREFERRED_TRANSCRIPT_VARIANT)).not.toContain('LOF CONSTR')

  const overlappingText = detailsText(overlappingGeneId, NON_PREFERRED_TRANSCRIPT_VARIANT)
  expect(overlappingText).toContain('TriploSensitive')
  expect(overlappingText).not.toContain('Constraint')
  expect(overlappingText).not.toContain('Shet')
  expect(overlappingText).not.toContain('haploinsufficiency')
  const overlappingBadges = badgeText(overlappingGeneId, NON_PREFERRED_TRANSCRIPT_VARIANT)
  expect(overlappingBadges).toContain('TS')
  expect(overlappingBadges).not.toContain('CONSTR')

  const withMainTranscript = transcriptId => ({
    ...NON_PREFERRED_TRANSCRIPT_VARIANT,
    mainTranscriptId: transcriptId,
    transcripts: {
      ...NON_PREFERRED_TRANSCRIPT_VARIANT.transcripts,
      [missenseGeneId]: [{ geneId: missenseGeneId, transcriptId }],
    },
  })
  const otherTranscriptText = detailsText(missenseGeneId, withMainTranscript('ENST00000641999'))
  expect(otherTranscriptText).toContain(
    'This transcript ranks as the 813th most constrained against missense variation among the 20,076 genes evaluated in gnomAD v4.1.2 (Z-score: 5.200).',
  )
  expect(otherTranscriptText).toContain(
    'This transcript ranks as the 1,501st most constrained against loss-of-function (LoF) mutations by LOEUF among the 20,076 genes evaluated in gnomAD v4.1.2 (LOEUF: 0.3000; pLI: 0.1000)',
  )

  const noEntryVariant = withMainTranscript('ENST00000999999')
  expect(detailsText(missenseGeneId, noEntryVariant)).toEqual('')
  expect(badgeText(missenseGeneId, noEntryVariant)).not.toContain('CONSTR')
  const selectedVariant = { ...NON_PREFERRED_TRANSCRIPT_VARIANT, selectedMainTranscriptId: 'ENST00000641515' }
  expect(badgeText(missenseGeneId, selectedVariant)).not.toContain('CONSTR')
  const selectedConstrainedVariant = {
    ...NON_PREFERRED_TRANSCRIPT_VARIANT, selectedMainTranscriptId: 'ENST00000641999',
    transcripts: {
      ...NON_PREFERRED_TRANSCRIPT_VARIANT.transcripts,
      [missenseGeneId]: [
        { geneId: missenseGeneId, transcriptId: 'ENST00000335137' },
        { geneId: missenseGeneId, transcriptId: 'ENST00000641999' },
      ],
    },
  }
  expect(detailsText(missenseGeneId, selectedConstrainedVariant)).toContain('ranks as the 813th most constrained')

  const noMainTranscriptVariant = { ...NON_PREFERRED_TRANSCRIPT_VARIANT, mainTranscriptId: null }
  expect(detailsText(missenseGeneId, noMainTranscriptVariant)).toContain('This gene ranks as the 1,349th most constrained')
  expect(badgeText(overlappingGeneId, noMainTranscriptVariant)).toContain('LOF CONSTR')

  const svText = geneId => detailsText(geneId, SV_VARIANT_WITH_CONSTRAINED_GENES)
  expect(svText(missenseGeneId)).toContain(
    'This gene ranks as the 1,349th most constrained against missense variation among the 20,076 genes evaluated in gnomAD v4.1.2 (Z-score: 4.137).',
  )
  expect(svText(overlappingGeneId)).toContain('This gene ranks as the 2,225th most constrained against loss-of-function')
  expect(badgeText(overlappingGeneId, SV_VARIANT_WITH_CONSTRAINED_GENES)).toContain('LOF CONSTR')
})
