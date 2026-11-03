import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import { getUser } from 'redux/selectors'
import Predictions from './Predictions'
import { STATE1, VARIANT, SV_VARIANT } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<Predictions store={store} variant={VARIANT} />)
  shallow(<Predictions store={store} variant={SV_VARIANT} />)
})

const AVI_PREDICTIONS = { cadd: '27.2', avi: '26.4' }

const renderPredictions = (predictions, variantOverrides = {}) => mount(
  <Provider store={configureStore()(STATE1)}>
    <Predictions variant={{ ...VARIANT, ...variantOverrides, predictions }} />
  </Provider>,
)

const findAviPrediction = wrapper => wrapper.find('Prediction').filterWhere(n => n.prop('field') === 'avi')

test('AlphaGenome AVI hover shows the color bands, the indel note and the citation', () => {
  const wrapper = renderPredictions(AVI_PREDICTIONS)

  expect(wrapper.text()).toContain('AlphaGenome AVI26.4')

  const aviPrediction = findAviPrediction(wrapper)
  expect(aviPrediction.prop('value')).toEqual('26.4')
  expect(aviPrediction.prop('color')).toEqual('orange')

  const popup = aviPrediction.find('Popup')
  expect(popup.prop('header')).toEqual('AlphaGenome AVI Color Ranges')
  const colorRanges = shallow(popup.prop('content'))
  expect(colorRanges.text()).toContain(' < 18')
  expect(colorRanges.text()).toContain(' 18 - 23')
  expect(colorRanges.text()).toContain(' 23 - 27')
  expect(colorRanges.text()).toContain(' >= 27')
  expect(colorRanges.text()).toContain('Indels have no AVI score')
  expect(colorRanges.find('a').prop('href')).toEqual('https://doi.org/10.1038/s41586-025-10014-0')
  expect(colorRanges.find('a').text()).toEqual('doi:10.1038/s41586-025-10014-0')
})

test('AlphaGenome AVI is hidden when the variant has no avi score', () => {
  const nullAvi = renderPredictions({ cadd: '27.2', avi: null })
  expect(nullAvi.text()).toContain('CADD27.2')
  expect(nullAvi.text()).not.toContain('AlphaGenome AVI')

  const missingAvi = renderPredictions({ cadd: '27.2' })
  expect(missingAvi.text()).toContain('CADD27.2')
  expect(missingAvi.text()).not.toContain('AlphaGenome AVI')
})

test('AlphaGenome AVI value links to the AlphaGenome Atlas variant page', () => {
  const variant = { chrom: '1', pos: 38724419, ref: 'T', alt: 'G' } // NOPMD
  const aviLink = findAviPrediction(renderPredictions({ avi: 18.6 }, variant)).find('a')
  expect(aviLink.prop('href')).toEqual(
    'https://deepmind.google.com/science/alphagenome/atlas?q=chr1:38724419:T%3EG&m=variant',
  )
  expect(aviLink.text()).toEqual('18.6')
})

test.each([
  [0, 'green'],
  [17.9, 'green'],
  [18, 'yellow'],
  [22.9, 'yellow'],
  [23, 'orange'],
  [26.9, 'orange'],
  [27, 'red'],
  [89, 'red'],
])('AlphaGenome AVI %s is colored %s', (avi, color) => {
  expect(findAviPrediction(renderPredictions({ avi })).prop('color')).toEqual(color)
})
