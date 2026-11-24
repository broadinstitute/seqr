import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { MemoryRouter, Route } from 'react-router-dom'

import { VARIANT } from 'shared/components/panel/fixtures'
import VariantSearchResults from './VariantSearchResults'

import { STATE } from '../fixtures'

jest.mock('../reducers', () => ({
  ...jest.requireActual('../reducers'),
  loadSingleSearchedVariant: () => ({ type: 'MOCK_LOAD_SINGLE_SEARCHED_VARIANT' }),
}))

// Like VariantLayout, spread unhandled props onto a Grid.Row DOM element
jest.mock('shared/components/panel/variants/Variants', () => {
  const { Grid } = jest.requireActual('semantic-ui-react')
  return ({ variants, ...props }) => (
    <Grid.Row {...props}>{variants.map(({ variantId }) => variantId).join()}</Grid.Row>
  )
})

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE)

  shallow(<VariantSearchResults store={store} match={{ params: {}}} />)
})

test('renders the single variant page', () => {
  const store = configureStore()({
    ...STATE,
    searchedVariantIds: [VARIANT.variantId],
    variantsById: { [VARIANT.variantId]: VARIANT },
  })

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={[`/variant_search/variant/${VARIANT.variantId}/family/F011652_1`]}>
        <Route path="/variant_search/variant/:variantId/family/:familyGuid" component={VariantSearchResults} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).toEqual(VARIANT.variantId)
})
