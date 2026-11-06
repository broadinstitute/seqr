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
  const wrapper = mount(
    <Provider store={store}>
      <GeneDetail geneId={geneId} />
    </Provider>,
  )
  const text = wrapper.text().replace(/\s+/g, ' ')

  expect(text).toContain('z-score: 4.137 (ranked 1349 most constrained out of 20076 genes under study)')
  expect(text).toContain('louef: 0.8198 (ranked 7627 most intolerant of LoF mutations out of 20076 genes under study)')
  expect(text).toContain('pLI-score: 0.7190 (ranked 4060 most intolerant of LoF mutations out of 20076 genes under study)')
  expect(text).toContain('NOTE: Missense constraint measures the depletion of missense variants observed in a gene')
  expect(text).toContain('observed in the gnomAD v4.1.2 data')
  expect(wrapper.find('a[href="https://gnomad.broadinstitute.org/help/constraint"]').map(link => link.text())).toEqual(
    ['Gene Constraint', 'Gene Constraint'],
  )
  expect(wrapper.find('a[href="https://pmc.ncbi.nlm.nih.gov/articles/PMC4222185/"]').text()).toEqual('Samocha et al., 2014')
})
