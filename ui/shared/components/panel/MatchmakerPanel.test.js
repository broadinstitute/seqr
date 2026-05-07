import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { getUser } from 'redux/selectors'
import { SubmissionGeneVariants, Phenotypes } from './MatchmakerPanel'
import { STATE1 } from './fixtures'
import configureStore from "redux-mock-store";

configure({ adapter: new Adapter() })

test('shallow-render SubmissionGeneVariants without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<SubmissionGeneVariants store={store} geneVariants={[
    { geneId: "ENSG00000228198", variantGuid: "SV0000002_1248367227_r0390_100" },
  ]} />)
})

test('shallow-render Phenotypes without crashing', () => {
  shallow(<Phenotypes phenotypes={[
    { id: "HP:0012638", label: "Abnormality of nervous system physiology", observed: "yes" },
    { id: "HP:0001371", label: "Flexion contracture", observed: "no" },
  ]} />)
})
