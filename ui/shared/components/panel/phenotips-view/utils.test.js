/* eslint-disable no-undef */

import groupFeaturesByPresentAbsent from './utils'

test('test groupFeaturesByPresentAbsent', () => {

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

  const groupedFeatures = groupFeaturesByPresentAbsent(features)

  expect(groupedFeatures.yes).toEqual(
    {
      'HP:0001507': [
        features[0],
        features[1],
      ],
      'HP:0040064': [
        features[2],
      ],
    },
    //['HP:0011405', 'HP:0004325', 'HP:0009821'],
  )
  expect(groupedFeatures.no).toEqual(
    {
      'HP:0003011': [
        features[3],
      ],
      'HP:0000707': [
        features[4],
      ],
    },
    //['HP:0001290', 'HP:0001250']
  )
})
