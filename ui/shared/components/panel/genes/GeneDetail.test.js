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
  expect(text).toContain('Missense constraint is a measure of the degree to which the number of missense variants found in this gene in gnomAD v4.1.2 is higher or lower than expected')
  expect(text).toContain('expected variation observed in the gnomAD v4.1.2 data')
  expect(text).not.toContain('ExAC')
  expect(text).not.toContain('Samocha')
  expect(wrapper.find('a[href="https://gnomad.broadinstitute.org/help/constraint"]').exists()).toBe(true)
  expect(wrapper.find('a[href^="ftp://"]').exists()).toBe(false)
})
