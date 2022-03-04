import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import HpoPanel, { getHpoTermsForCategory } from './HpoPanel'

import { STATE1 } from './fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {

  shallow(<HpoPanel individual={STATE1.individualsByGuid.I021474_na19679}/>)
})

test('test getHpoTermsForCategory', () => {

  const features = [
    {
      category: 'HP:0001507',
      id: 'HP:0011405',
      label: 'Childhood onset short-limb short stature',
    },
    {
      category: 'HP:0001507',
      id: 'HP:0004325',
      label: 'Decreased body weight',
    },
    {
      category: 'HP:0040064',
      id: 'HP:0009821',
      label: 'Forearm undergrowth',
    },
  ]

  const nonstandardFeatures = [
    {
      categories: [{ id: 'HP:0001507', label: 'Abnormal Growth' }],
      id: 'Generalized hypotonia',
    },
    {
      categories: [{ id: 'HP:0001507' }, { id: 'HP:0001234', label: 'Skeletal system' }],
      id: 'Seizures',
    },
    {
      id: 'Vague phenotype',
    },
  ]

  expect(getHpoTermsForCategory(features, nonstandardFeatures)).toEqual([
    {
      categoryName: 'Growth Abnormality',
      terms: [
        features[0],
        features[1],
        nonstandardFeatures[0],
      ]
    },
    {
      categoryName: 'Growth Abnormality, Skeletal system',
      terms: [
        nonstandardFeatures[1],
      ]
    },
    {
      categoryName: 'Limbs',
      terms: [
        features[2],
      ]
    },
    {
      categoryName: 'Other',
      terms: [
        nonstandardFeatures[2],
      ]
    },
  ])
})

