import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import GeneDetail from './GeneDetail'

import { STATE1, MISSENSE_CONSTRAINED_GENE, LOF_CONSTRAINED_GENE, CONSTRAINT_TRANSCRIPTS_BY_ID } from '../fixtures'

jest.mock('../../graph/Gtex', () => () => <div>Gtex</div>)
jest.mock('../view-fields/NoteListFieldView', () => () => <div>NoteListFieldView</div>)

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<GeneDetail store={store} geneId="TTN" />)
})

const mountGeneDetail = (gene, transcriptsById = CONSTRAINT_TRANSCRIPTS_BY_ID) => {
  const store = configureStore([thunk])({
    ...STATE1, genesById: { [gene.geneId]: gene }, transcriptsById, genesLoading: { isLoading: false },
  })
  return mount(
    <Provider store={store}>
      <GeneDetail geneId={gene.geneId} />
    </Provider>,
  )
}

const withConstraints = constraints => ({
  ...CONSTRAINT_TRANSCRIPTS_BY_ID,
  ENST00000641515: {
    ...CONSTRAINT_TRANSCRIPTS_BY_ID.ENST00000641515,
    constraints: { ...CONSTRAINT_TRANSCRIPTS_BY_ID.ENST00000641515.constraints, ...constraints },
  },
})

test('constraint stats name gnomAD v4.1.2 and link to its constraint help', () => {
  const wrapper = mountGeneDetail(MISSENSE_CONSTRAINED_GENE)
  const text = wrapper.text().replace(/\s+/g, ' ')

  expect(text).toContain('z-score: 4.137 (ranked 1349 most constrained out of 20076 genes under study)')
  expect(text).toContain('louef: 0.8198 (ranked 7627 most intolerant of LoF mutations out of 20076 genes under study)')
  expect(text).toContain('pLI-score: 0.7190 (ranked 4060 most intolerant of LoF mutations out of 20076 genes under study)')
  expect(text).not.toContain('z-score: 5.200')
  expect(text).toContain('genes under study)NOTE: Missense')
  expect(text).toContain('NOTE: Missense constraint measures the depletion of missense variants observed in a gene')
  expect(text).toContain('observed in the gnomAD v4.1.2 data')
  expect(wrapper.find('a[href="https://gnomad.broadinstitute.org/help/constraint"]').map(link => link.text())).toEqual(
    ['Gene Constraint', 'Gene Constraint'],
  )
  expect(wrapper.find('a[href="https://pmc.ncbi.nlm.nih.gov/articles/PMC4222185/"]').text()).toEqual('Samocha et al., 2014')

  const noScoreCount = geneText => (geneText.match(/No score available/g) || []).length
  const nullConstraintsText = mountGeneDetail(
    MISSENSE_CONSTRAINED_GENE, withConstraints({ misZ: null, louef: null, pli: null }),
  ).text()
  expect(nullConstraintsText).not.toContain('ranked')
  expect(noScoreCount(nullConstraintsText)).toEqual(noScoreCount(text) + 2)

  const noTranscriptsText = mountGeneDetail(MISSENSE_CONSTRAINED_GENE, {}).text()
  expect(noTranscriptsText).not.toContain('ranked')
  expect(noScoreCount(noTranscriptsText)).toEqual(noScoreCount(text) + 2)
})

test('constraint stats fall back to the canonical transcript when there is no MANE Select transcript', () => {
  const text = mountGeneDetail(LOF_CONSTRAINED_GENE).text().replace(/\s+/g, ' ')

  expect(text).toContain('louef: 0.3995 (ranked 2225 most intolerant of LoF mutations out of 20076 genes under study)')
})

test('stats help popup says which transcript the stats are from', () => {
  const statsHelp = mountGeneDetail(MISSENSE_CONSTRAINED_GENE).find('Popup').filterWhere(
    popup => popup.find('HelpIcon').exists(),
  )

  expect(statsHelp.prop('content')).toEqual(
    'Information here pertains to the MANE Select or canonical transcript for a given gene',
  )
})
