import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import PhenotipsDataPanel, { getHpoTermsForCategory } from './PhenotipsDataPanel'

import { STATE1 } from './fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
   project: PropTypes.object.isRequired,
   individual: PropTypes.object.isRequired,
   showDetails: PropTypes.bool.isRequired,
   showPhenotipsModal: PropTypes.func.isRequired,
   */

  const props = {
    project: STATE1.project,
    individual: STATE1.individualsByGuid.I021474_na19679,
    showDetails: true,
    showEditPhenotipsLink: true,
    showPhenotipsModal: () => {},
  }

  shallow(<PhenotipsDataPanel {...props} />)

  const props2 = { ...props, showDetails: false }

  shallow(<PhenotipsDataPanel {...props2} />)
})


test('test getHpoTermsForCategory', () => {

  const features = [
    {
      category: 'HP:0001507',
      id: 'HP:0011405',
      label: 'Childhood onset short-limb short stature',
      observed: 'yes',
      type: 'phenotype',
    },
    {
      category: 'HP:0001507',
      id: 'HP:0004325',
      label: 'Decreased body weight',
      observed: 'yes',
      type: 'phenotype',
    },
    {
      category: 'HP:0040064',
      id: 'HP:0009821',
      label: 'Forearm undergrowth',
      observed: 'yes',
      type: 'phenotype',
    },
    {
      category: 'HP:0003011',
      id: 'HP:0001290',
      label: 'Generalized hypotonia',
      observed: 'no',
      type: 'phenotype',
    },
    {
      category: 'HP:0000707',
      id: 'HP:0001250',
      label: 'Seizures',
      observed: 'no',
      type: 'phenotype',
    },
  ]

  expect(getHpoTermsForCategory('yes')(features)).toEqual([
    {
      categoryName: 'Growth Abnormality',
      terms: [
        features[0],
        features[1],
      ]
    },
    {
      categoryName: 'Limbs',
      terms: [
        features[2],
      ]
    },
  ])
  expect(getHpoTermsForCategory('no')(features)).toEqual([
    {
      categoryName: 'Musculature',
      terms: [
        features[3],
      ]
    },
    {
      categoryName: 'Nervous System',
      terms: [
        features[4],
      ]
    },
  ])
})

