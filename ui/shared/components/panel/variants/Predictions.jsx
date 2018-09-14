import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import ButtonLink from 'shared/components/buttons/ButtonLink'
import { Icon, Transition } from 'semantic-ui-react'

import { snakecaseToTitlecase } from 'shared/utils/stringUtils'

const INDICATOR_MAP = {
  D: { color: 'red', value: 'damaging' },
  A: { color: 'red', value: 'disease causing' },
  T: { color: 'green', value: 'tolerated' },
  N: { color: 'green', value: 'polymorphism' },
  P: { color: 'green', value: 'polymorphism' },
  B: { color: 'green', value: 'benign' },
}

const POLYPHEN_MAP = {
  D: { value: 'probably damaging' },
  P: { color: 'yellow', value: 'possibly damaging' },
}

const MUTTASTER_MAP = {
  D: { value: 'disease causing' },
}


const PredictionValue = styled.span`
  font-weight: bolder;
  color: grey;
  text-transform: uppercase;
`

const StyledButtonLink = styled(ButtonLink)`
  padding-left: 20px;
`

const NUM_TO_SHOW_ABOVE_THE_FOLD = 6 // how many predictors to show immediately


const predictionFieldValue = (predictions, { field, dangerThreshold, warningThreshold, indicatorMap, noSeverity }) => {
  let value = predictions[field]
  if (noSeverity || value === null) {
    return { value }
  }

  if (dangerThreshold) {
    value = parseFloat(value).toPrecision(2)
    if (value >= dangerThreshold) {
      return { value, color: 'red' }
    } else if (value >= warningThreshold) {
      return { value, color: 'yellow' }
    }
    return { value, color: 'green' }
  }

  return indicatorMap ? { ...INDICATOR_MAP[value[0]], ...indicatorMap[value[0]] } : INDICATOR_MAP[value[0]]
}

const Prediction = ({ field, value, color }) =>
  <div>
    <Icon name="circle" size="small" color={color} /> {snakecaseToTitlecase(field)}
    <PredictionValue> {value}</PredictionValue>
  </div>

Prediction.propTypes = {
  field: PropTypes.string.isRequired,
  value: PropTypes.any.isRequired,
  color: PropTypes.string,
}

const PREDICTOR_FIELDS = [
  { field: 'cadd', warningThreshold: 10, dangerThreshold: 20 },
  { field: 'dann', warningThreshold: 0.93, dangerThreshold: 0.96 },
  { field: 'revel', warningThreshold: 0.5, dangerThreshold: 0.75 },
  { field: 'eigen', warningThreshold: 1, dangerThreshold: 2 },
  { field: 'mpc', warningThreshold: 1, dangerThreshold: 2 },
  { field: 'primate_ai', warningThreshold: 0.5, dangerThreshold: 0.7 },
  { field: 'polyphen', indicatorMap: POLYPHEN_MAP },
  { field: 'sift' },
  { field: 'mut_taster', indicatorMap: MUTTASTER_MAP },
  { field: 'fathmm' },
  { field: 'metasvm' },
  { field: 'gerp_rs', noSeverity: true },
  { field: 'phastcons_100_vert', noSeverity: true },
]

export default class Predictions extends React.PureComponent {
  static propTypes = {
    predictions: PropTypes.object,
  }

  constructor(props) {
    super(props)

    this.state = { showMore: false }
  }

  toggleShowMore = () => {
    this.setState({ showMore: !this.state.showMore })
  }

  render() {
    const { predictions } = this.props

    if (!predictions) {
      return null
    }

    const predictorFields = PREDICTOR_FIELDS.map(predictorField =>
      ({ field: predictorField.field, ...predictionFieldValue(predictions, predictorField) }),
    ).filter(predictorField => predictorField.value !== null && predictorField.value !== undefined)
    return (
      <div>
        {
          predictorFields.slice(0, NUM_TO_SHOW_ABOVE_THE_FOLD).map(predictorField =>
            <Prediction key={predictorField.field} {...predictorField} />)
        }
        {
          predictorFields.length > NUM_TO_SHOW_ABOVE_THE_FOLD &&
            <Transition.Group animation="fade down" duration="500">
              {
                this.state.showMore && predictorFields.slice(NUM_TO_SHOW_ABOVE_THE_FOLD).map(predictorField =>
                  <Prediction key={predictorField.field} {...predictorField} />,
                )
              }
              <StyledButtonLink onClick={this.toggleShowMore}>
                {this.state.showMore ? 'hide' : 'show more...'}
              </StyledButtonLink>
            </Transition.Group>
        }
      </div>
    )
  }
}

