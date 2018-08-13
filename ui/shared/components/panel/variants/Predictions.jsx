import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Icon, Transition } from 'semantic-ui-react'


const SEVERITY_MAP = {
  damaging: 'red',
  probably_damaging: 'red',
  disease_causing: 'red',
  possibly_damaging: 'yellow',
  benign: 'green',
  tolerated: 'green',
  polymorphism: 'green',
}

const PredictionValue = styled.span`
  font-weight: bolder;
  color: grey;
  text-transform: uppercase;
`

const LinkButton = styled.span.attrs({ role: 'button', tabIndex: '0' })`
  cursor: pointer;
  padding-left: 20px;
`

const NUM_TO_SHOW_ABOVE_THE_FOLD = 6 // how many predictors to show immediately

const Prediction = ({ field, annotation, dangerThreshold, warningThreshold, name }) => {
  let value = annotation[field]
  if (!value) {
    return null
  }

  let color
  if (dangerThreshold) {
    value = parseFloat(value).toPrecision(2)
    if (value >= dangerThreshold) {
      color = 'red'
    } else if (value >= warningThreshold) {
      color = 'yellow'
    } else {
      color = 'green'
    }
  } else {
    color = SEVERITY_MAP[value]
    if (value) {
      value = `${value}`.replace('_', ' ')
    }
  }

  if (!name) {
    name = field.replace(/_/g, ' ').toUpperCase()
  }

  return (
    <div>
      <Icon name="circle" size="small" color={color} /> {name}
      <PredictionValue> {value}</PredictionValue>
    </div>)
}

Prediction.propTypes = {
  field: PropTypes.string.isRequired,
  annotation: PropTypes.object,
  dangerThreshold: PropTypes.number,
  warningThreshold: PropTypes.number,
  name: PropTypes.string,
}

const PREDICTOR_FIELDS = [
  { field: 'cadd_phred', name: 'CADD', warningThreshold: 10, dangerThreshold: 20 },
  { field: 'dann_score', name: 'DANN', warningThreshold: 0.93, dangerThreshold: 0.96 },
  { field: 'revel_score', name: 'REVEL', warningThreshold: 0.5, dangerThreshold: 0.75 },
  { field: 'eigen_phred', name: 'EIGEN', warningThreshold: 1, dangerThreshold: 2 },
  { field: 'mpc_score', name: 'MPC', warningThreshold: 1, dangerThreshold: 2 },
  { field: 'primate_ai_score', name: 'PMT AI', warningThreshold: 0.5, dangerThreshold: 0.7 },
  { field: 'polyphen' },
  { field: 'sift' },
  { field: 'mut_taster' },
  { field: 'fathmm' },
  { field: 'metasvm' },
  { field: 'gerp_rs' },
  { field: 'phastcons100vert' },
]

export default class Predictions extends React.Component {
  static propTypes = {
    annotation: PropTypes.object,
  }

  constructor(props) {
    super(props)

    this.state = { showMore: false }
  }

  render() {
    const { annotation } = this.props

    if (!annotation) {
      return null
    }

    const predictorFields = PREDICTOR_FIELDS.filter(predictorField => annotation[predictorField.field] != null)
    const predictorFieldsAboveTheFold = predictorFields.slice(0, NUM_TO_SHOW_ABOVE_THE_FOLD)
    const morePredictorFields = predictorFields.slice(NUM_TO_SHOW_ABOVE_THE_FOLD)
    return (
      <div>
        {
          predictorFieldsAboveTheFold.map(predictorField =>
            <Prediction key={predictorField.field} annotation={annotation} {...predictorField} />)
        }
        {
          morePredictorFields ?
            <Transition.Group animation="fade down" duration="500">
              {
                this.state.showMore ?
                  <div>
                    {
                      morePredictorFields.map(predictorField => <Prediction key={predictorField.field} field={predictorField.field} annotation={annotation} />)
                    }
                    <LinkButton onClick={() => this.setState({ showMore: false })}>hide</LinkButton>
                  </div>
                :
                  morePredictorFields.some(predictorField => annotation[predictorField.field] != null) &&
                  <LinkButton onClick={() => this.setState({ showMore: true })}>show more...</LinkButton>
              }
            </Transition.Group>
          : null
        }
      </div>
    )
  }
}

