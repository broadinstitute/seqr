import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import Transcripts from './Transcripts'

import {
  STATE1, GENE, VARIANT, MISSENSE_CONSTRAINED_GENE, LOF_CONSTRAINED_GENE, CONSTRAINT_TRANSCRIPTS_BY_ID,
  NON_PREFERRED_TRANSCRIPT_VARIANT,
} from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<Transcripts store={store} gene={GENE} variant={VARIANT} />)
})

test('shows constraint labels only for main gene transcripts that have constraint scores', () => {
  const store = configureStore()({
    ...STATE1,
    genesById: {
      [MISSENSE_CONSTRAINED_GENE.geneId]: {
        ...MISSENSE_CONSTRAINED_GENE, cnSensitivity: { phi: 0.99 }, sHet: { postMean: 0.5 },
      },
      [LOF_CONSTRAINED_GENE.geneId]: LOF_CONSTRAINED_GENE,
    },
    transcriptsById: CONSTRAINT_TRANSCRIPTS_BY_ID,
    modal: {},
  })
  const mountTranscripts = variant => mount(
    <Provider store={store}>
      <Transcripts variant={variant} />
    </Provider>,
  )
  const labelText = variant => mountTranscripts(variant).text()

  const wrapper = mountTranscripts(NON_PREFERRED_TRANSCRIPT_VARIANT)
  const text = wrapper.text()
  expect(text.match(/MISSENSE CONSTR/g)).toHaveLength(2)
  expect(text).not.toContain('LOF CONSTR')
  const popupText = wrapper.find('Popup').map(popup => mount(<div>{popup.prop('content')}</div>).text()).join(' ')
  expect(popupText).toContain('This transcript ranks as the 3,201st')

  const mainTranscriptText = labelText(
    { ...NON_PREFERRED_TRANSCRIPT_VARIANT, selectedMainTranscriptId: 'ENST00000611883' },
  )
  expect(mainTranscriptText.match(/LOF CONSTR/g)).toHaveLength(1)
  expect(mainTranscriptText).not.toContain('MISSENSE CONSTR')

  const svText = labelText({ ...NON_PREFERRED_TRANSCRIPT_VARIANT, svType: 'DEL' })
  expect(svText).not.toContain('CONSTR')
})
