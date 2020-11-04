import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Label } from 'semantic-ui-react'

import { VerticalSpacer } from 'shared/components/Spacers'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'

const IndentedContainer = styled.div`
  padding-left: 20px;
`

const UNKNOWN_CATEGORY = 'Other'

export const CATEGORY_NAMES = {
  'HP:0000119': 'Genitourinary',
  'HP:0000152': 'Head or Neck',
  'HP:0000478': 'Eye',
  'HP:0000598': 'Ear',
  'HP:0000707': 'Nervous System',
  'HP:0000769': 'Breast',
  'HP:0000818': 'Endocrine',
  'HP:0000924': 'Skeletal',
  'HP:0001197': 'Prenatal or birth',
  'HP:0001507': 'Growth Abnormality',
  'HP:0001574': 'Integument',
  'HP:0001608': 'Voice',
  'HP:0001626': 'Cardiovascular',
  'HP:0001871': 'Blood',
  'HP:0001939': 'Metabolism/Homeostasis',
  'HP:0002086': 'Respiratory',
  'HP:0002664': 'Neoplasm',
  'HP:0002715': 'Immune System',
  'HP:0003011': 'Musculature',
  'HP:0003549': 'Connective Tissue',
  'HP:0025031': 'Digestive',
  'HP:0040064': 'Limbs',
  'HP:0045027': 'Thoracic Cavity',
  'HP:0025354': 'Cellular Phenotype',
  'HP:0025142': 'Constitution',
  'HP:0033127': 'Musculoskeletal',
}

export const getHpoTermsForCategory = (features, nonstandardFeatures) => {
  const hpoTermsByCategory = (features || []).reduce((acc, hpoTerm) => {
    const category = CATEGORY_NAMES[hpoTerm.category] || UNKNOWN_CATEGORY
    if (!acc[category]) {
      acc[category] = [] //init array of features
    }
    acc[category].push(hpoTerm)
    return acc
  }, {})

  if (nonstandardFeatures) {
    nonstandardFeatures.reduce((acc, term) => {
      const category = (term.categories || ['']).map(categoryTerm =>
        CATEGORY_NAMES[categoryTerm.id] || categoryTerm.label || UNKNOWN_CATEGORY,
      ).sort().join(', ')
      if (!acc[category]) {
        acc[category] = [] //init array of features
      }

      acc[category].push(term)
      return acc
    }, hpoTermsByCategory)
  }

  return Object.entries(hpoTermsByCategory).map(
    ([categoryName, terms]) => ({ categoryName, terms })).sort((a, b) =>
    a.categoryName.localeCompare(b.categoryName))
}

const FeatureSection = React.memo(({ features, nonstandardFeatures, title, color }) => {
  if ((features || []).length < 1 && (nonstandardFeatures || []).length < 1) {
    return null
  }
  const termsByCategory = getHpoTermsForCategory(features, nonstandardFeatures)
  return (
    <div>
      <VerticalSpacer height={10} />
      <Label basic horizontal color={color} content={title} />
      <VerticalSpacer height={5} />
      <IndentedContainer>
        {
          termsByCategory.map(category =>
            <div key={category.categoryName}>
              <b>{category.categoryName}</b>: {
                (category.terms || []).map(
                  (hpoTerm, i) => {
                    const qualifiers = (hpoTerm.qualifiers || []).map(({ type, label }) =>
                      <span key={type}> - <b>{snakecaseToTitlecase(type)}:</b> {label}</span>,
                    )
                    const notes = hpoTerm.notes ? <small> ({hpoTerm.notes})</small> : null
                    return <span key={hpoTerm.id}>{hpoTerm.label || hpoTerm.id}{qualifiers}{notes}{i < category.terms.length - 1 ? ', ' : ''}</span>
                  },
                )
              }
            </div>,
          )
        }
      </IndentedContainer>
    </div>
  )
})

FeatureSection.propTypes = {
  features: PropTypes.array,
  nonstandardFeatures: PropTypes.array,
  title: PropTypes.string,
  color: PropTypes.string,
}

const HpoPanel = React.memo(({ individual }) => [
  <FeatureSection
    key="present"
    features={individual.features}
    nonstandardFeatures={individual.nonstandardFeatures}
    title="Present"
    color="green"
  />,
  <FeatureSection
    key="absent"
    features={individual.absentFeatures}
    nonstandardFeatures={individual.absentNonstandardFeatures}
    title="Not Present"
    color="red"
  />,
])

HpoPanel.propTypes = {
  individual: PropTypes.object.isRequired,
}

export default HpoPanel
