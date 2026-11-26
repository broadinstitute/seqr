import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import Annotations from './Annotations'
import { STATE1, VARIANT, SV_VARIANT, LOCUS_LIST, LOCUS_LIST_GUID } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<Annotations store={store} variant={VARIANT} />)
  shallow(<Annotations store={store} variant={SV_VARIANT} />)
})

test('labels variants in project gene list intervals', () => {
  const interval = { locusListGuid: LOCUS_LIST_GUID, genomeVersion: '37', chrom: '1', start: 248367000, end: 248368000 }
  const store = configureStore()({
    ...STATE1,
    projectsByGuid: {
      R0237_1000_genomes_demo: { ...STATE1.projectsByGuid.R0237_1000_genomes_demo, locusListGuids: [LOCUS_LIST_GUID] },
    },
    familiesByGuid: { ...STATE1.familiesByGuid, F011652_2: STATE1.familiesByGuid.F011652_1 },
    locusListsByGuid: { [LOCUS_LIST_GUID]: { ...LOCUS_LIST, intervals: [interval] } },
  })
  const getLabels = variant => mount(
    <Provider store={store}><MemoryRouter><Annotations variant={variant} /></MemoryRouter></Provider>,
  ).find('Label').map(label => label.text())

  expect(getLabels(VARIANT)).toEqual([LOCUS_LIST.name])
  expect(getLabels({ ...VARIANT, familyGuids: ['F011652_1', 'F011652_2'] })).toEqual([LOCUS_LIST.name])
  expect(getLabels({ ...VARIANT, pos: 248369000 })).toEqual([])
})
