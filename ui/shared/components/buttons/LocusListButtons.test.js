import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { flushAll } from 'shared/utils/testHelpers'
import { CreateLocusList, UpdateLocusList, DeleteLocusList, DeleteLocusListButton } from './LocusListButtons'

import { STATE1, LOCUS_LIST, LOCUS_LIST_GUID } from '../panel/fixtures'

configure({ adapter: new Adapter() })

const HISTORY = ['/summary_data/gene_lists', `/summary_data/gene_lists/${LOCUS_LIST_GUID}`]

test('shallow-render without crashing', () => {
  shallow(<CreateLocusList />)
  shallow(<UpdateLocusList locusList={LOCUS_LIST} />)
  shallow(<DeleteLocusList locusList={LOCUS_LIST} />)
})

test('deleting a gene list from its page replaces the page in the browser history', async () => {
  const store = configureStore([thunk])(STATE1)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={HISTORY} initialIndex={1}>
        <DeleteLocusListButton locusList={LOCUS_LIST} />
      </MemoryRouter>
    </Provider>,
  )

  wrapper.find('Confirm').prop('onConfirm')()
  await flushAll()

  expect(wrapper.find('Router').prop('history').entries.map(({ pathname }) => pathname)).toEqual(
    ['/summary_data/gene_lists', '/summary_data/gene_lists'],
  )
})
