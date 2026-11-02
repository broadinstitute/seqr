import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { Grid, Header } from 'semantic-ui-react'

import { NO_SV_IN_SILICO_GROUPS } from 'shared/utils/constants'
import { IN_SILICO_PANEL } from './VariantSearchFormPanelConfigs'

configure({ adapter: new Adapter() })

test('AlphaGenome AVI is a Coding/Noncoding numeric in-silico filter from Phred 0 up to 99', () => {
  expect(IN_SILICO_PANEL.fields.find(({ name }) => name === 'avi')).toMatchObject({
    label: 'AlphaGenome AVI', group: 'Coding/Noncoding', type: 'number', min: 0, max: 99, step: 1,
  })
})

test('AlphaGenome AVI filter is placed in the Coding/Noncoding row', () => {
  const components = IN_SILICO_PANEL.fields.map(({ name }) => <div key={name} id={name} />)
  const wrapper = shallow(IN_SILICO_PANEL.fieldLayout(components, NO_SV_IN_SILICO_GROUPS))

  const codingRow = wrapper.find(Grid.Row).filterWhere(
    row => row.find(Header).filterWhere(header => header.prop('content') === 'Coding/Noncoding').exists(),
  )
  expect(codingRow).toHaveLength(1)
  expect(codingRow.find('#avi').exists()).toBe(true)
})
