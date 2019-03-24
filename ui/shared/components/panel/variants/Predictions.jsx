import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Icon, Transition } from 'semantic-ui-react'

import { getGenesById } from 'redux/selectors'
import { PREDICTION_INDICATOR_MAP, POLYPHEN_MAP, MUTTASTER_MAP } from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import { HorizontalSpacer } from '../../Spacers'
import { ButtonLink } from '../../StyledComponents'


const PredictionValue = styled.span`
  font-weight: bolder;
  color: black;
  text-transform: uppercase;
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

  return indicatorMap ? { ...PREDICTION_INDICATOR_MAP[value[0]], ...indicatorMap[value[0]] } : PREDICTION_INDICATOR_MAP[value[0]]
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
  { field: 'splice_ai', warningThreshold: 0.5, dangerThreshold: 0.8 },
  { field: 'polyphen', indicatorMap: POLYPHEN_MAP },
  { field: 'sift' },
  { field: 'mut_taster', indicatorMap: MUTTASTER_MAP },
  { field: 'fathmm' },
  { field: 'metasvm' },
  { field: 'gerp_rs', noSeverity: true },
  { field: 'phastcons_100_vert', noSeverity: true },
]

class Predictions extends React.PureComponent {
  static propTypes = {
    variant: PropTypes.object,
    gene: PropTypes.object,
  }

  constructor(props) {
    super(props)

    this.state = { showMore: false }
  }

  toggleShowMore = () => {
    this.setState({ showMore: !this.state.showMore })
  }

  render() {
    const { predictions } = this.props.variant

    if (!predictions) {
      return null
    }

    const genePredictors = {}
    if (this.props.gene && this.props.gene.primateAi) {
      genePredictors.primate_ai = {
        field: 'primate_ai',
        warningThreshold: this.props.gene.primateAi.percentile25,
        dangerThreshold: this.props.gene.primateAi.percentile75,
      }
    }

    const predictorFields = PREDICTOR_FIELDS.map(predictorField => ({
      field: predictorField.field,
      ...predictionFieldValue(predictions, genePredictors[predictorField.field] || predictorField),
    })).filter(predictorField => predictorField.value !== null && predictorField.value !== undefined)
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
              <ButtonLink onClick={this.toggleShowMore}>
                <HorizontalSpacer width={20} />
                {this.state.showMore ? 'hide' : 'show more...'}
              </ButtonLink>
            </Transition.Group>
        }
      </div>
    )
  }
}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.variant.mainTranscript.geneId],
})

export default connect(mapStateToProps)(Predictions)

