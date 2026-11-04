import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import GeneDetail from './GeneDetail'

import { STATE1, MISSENSE_CONSTRAINED_GENE } from '../fixtures'

jest.mock('../../graph/Gtex', () => () => <div>Gtex</div>)
jest.mock('../view-fields/NoteListFieldView', () => () => <div>NoteListFieldView</div>)

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<GeneDetail store={store} geneId="TTN" />)
})

test('constraint stats name gnomAD v4.1.2 and link to its constraint help', () => {
  const { geneId } = MISSENSE_CONSTRAINED_GENE
  const store = configureStore([thunk])({
    ...STATE1, genesById: { [geneId]: MISSENSE_CONSTRAINED_GENE }, genesLoading: { isLoading: false },
  })
  const wrapper = mount(<Provider store={store}><GeneDetail geneId={geneId} /></Provider>)
  const text = wrapper.text().replace(/\s+/g, ' ')

  expect(text).toContain('z-score: 4.137 (ranked 1348 most constrained out of 20076 genes under study)')
  expect(text).toContain('louef: 0.8198 (ranked 7626 most intolerant of LoF mutations out of 20076 genes under study)')
  expect(text).toContain('pLI-score: 0.7190 (ranked 4059 most intolerant of LoF mutations out of 20076 genes under study)')
  expect(text).toContain(
    'NOTE: Missense constraint measures the depletion of missense variants observed in a gene relative to the number expected under a statistical model that accounts for local sequence context and other mutational factors [Samocha et al., 2014]. A higher positive Z-score indicates stronger constraint, meaning fewer missense variants are observed than expected. This metric can be particularly useful for prioritizing genes associated with dominant disorders, especially when a large proportion of the protein is functionally constrained. See Gene Constraint for more information.',
  )
  expect(text).toContain(
    'NOTE: These metrics are based on the amount of expected variation observed in the gnomAD v4.1.2 data and is a measure of how likely the gene is to be intolerant of loss-of-function mutations. See Gene Constraint for more information.',
  )
  expect(text).not.toContain('ExAC')
  const constraintLinks = wrapper.find('a[href="https://gnomad.broadinstitute.org/help/constraint"]')
  expect(constraintLinks.map(link => link.text())).toEqual(['Gene Constraint', 'Gene Constraint'])
  expect(constraintLinks.map(link => link.prop('target'))).toEqual(['_blank', '_blank'])
  expect(constraintLinks.map(link => link.prop('rel'))).toEqual(['noreferrer', 'noreferrer'])
  expect(wrapper.find('a[href^="ftp://"]').exists()).toBe(false)
})
