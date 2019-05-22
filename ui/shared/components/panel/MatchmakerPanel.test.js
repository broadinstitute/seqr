import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getUser } from 'redux/selectors'
import { SubmissionGeneVariants, Phenotypes } from './MatchmakerPanel'
import { STATE1 } from './fixtures'
import configureStore from "redux-mock-store";

configure({ adapter: new Adapter() })

test('shallow-render SubmissionGeneVariants without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<SubmissionGeneVariants store={store} geneVariants={[
    { alt: "C", chrom: "22", geneId: "ENSG00000228198", genomeVersion: "38", pos: 46436281, ref: "G" },
  ]} />)
})

test('shallow-render Phenotypes without crashing', () => {
  shallow(<Phenotypes phenotypes={[
    { id: "HP:0012638", label: "Abnormality of nervous system physiology", observed: "yes" },
    { id: "HP:0001371", label: "Flexion contracture", observed: "no" },
  ]} />)
})
