import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Icon, Transition, Popup } from 'semantic-ui-react'

import { getGenesById } from 'redux/selectors'
import { PREDICTION_INDICATOR_MAP, POLYPHEN_MAP, MUTTASTER_MAP, getVariantMainGeneId } from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import { HorizontalSpacer } from '../../Spacers'
import { ButtonLink } from '../../StyledComponents'


const PredictionValue = styled.span`
  font-weight: bolder;
  color: black;
  text-transform: uppercase;
`

const NUM_TO_SHOW_ABOVE_THE_FOLD = 6 // how many predictors to show immediately


const predictionFieldValue = (predictions, { field, dangerThreshold, warningThreshold, indicatorMap, noSeverity, infoField, infoTitle }) => {
  let value = predictions[field]
  if (noSeverity || value === null || value === undefined) {
    return { value }
  }

  const infoValue = predictions[infoField]

  if (dangerThreshold) {
    value = parseFloat(value).toPrecision(2)
    let color = 'green'
    if (value >= dangerThreshold) {
      color = 'red'
    } else if (value >= warningThreshold) {
      color = 'yellow'
    }
    return { value, color, infoValue, infoTitle, dangerThreshold, warningThreshold }
  }

  return indicatorMap ? { ...PREDICTION_INDICATOR_MAP[value[0]], ...indicatorMap[value[0]] } : PREDICTION_INDICATOR_MAP[value[0]]
}

const Prediction = ({ field, value, color, infoValue, infoTitle, warningThreshold, dangerThreshold }) => {
  const indicator = infoValue ? <Popup
    header={infoTitle}
    content={infoValue}
    trigger={<Icon name="question circle" size="small" color={color} />}
  /> : <Icon name="circle" size="small" color={color} />
  const fieldName = snakecaseToTitlecase(field)
  const fieldDisplay = dangerThreshold ? <Popup
    header={`${fieldName} Color Ranges`}
    content={
      <div>
        <div>Red &gt; {dangerThreshold}</div>
        <div>Yellow &gt; {warningThreshold}</div>
      </div>}
    trigger={<span>{fieldName}</span>}
  /> : fieldName

  return (
    <div>
      {indicator} {fieldDisplay}
      <PredictionValue> {value}</PredictionValue>
    </div>
  )
}


Prediction.propTypes = {
  field: PropTypes.string.isRequired,
  value: PropTypes.any.isRequired,
  infoValue: PropTypes.any,
  infoTitle: PropTypes.string,
  color: PropTypes.string,
  warningThreshold: PropTypes.number,
  dangerThreshold: PropTypes.number,
}

const PREDICTOR_FIELDS = [
  { field: 'cadd', warningThreshold: 10, dangerThreshold: 20 },
  { field: 'revel', warningThreshold: 0.5, dangerThreshold: 0.75 },
  { field: 'primate_ai', warningThreshold: 0.5, dangerThreshold: 0.7 },
  { field: 'mpc', warningThreshold: 1, dangerThreshold: 2 },
  { field: 'splice_ai', warningThreshold: 0.5, dangerThreshold: 0.8, infoField: 'splice_ai_consequence', infoTitle: 'Predicted Consequence' },
  { field: 'eigen', warningThreshold: 1, dangerThreshold: 2 },
  { field: 'dann', warningThreshold: 0.93, dangerThreshold: 0.96 },
  { field: 'strvctvre', warningThreshold: 0.5, dangerThreshold: 0.75 },
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
  gene: getGenesById(state)[getVariantMainGeneId(ownProps.variant)],
})

export default connect(mapStateToProps)(Predictions)

