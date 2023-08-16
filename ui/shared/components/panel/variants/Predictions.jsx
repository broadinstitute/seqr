import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Icon, Transition, Popup } from 'semantic-ui-react'

import { getGenesById } from 'redux/selectors'
import { PREDICTOR_FIELDS, getPredictColor, getVariantMainGeneId } from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import { HorizontalSpacer } from '../../Spacers'
import { ButtonLink } from '../../StyledComponents'

const PredictionValue = styled.span`
  margin-left: 5px;
  font-weight: bolder;
  color: black;
  text-transform: uppercase;
`

const NUM_TO_SHOW_ABOVE_THE_FOLD = 6 // how many predictors to show immediately

const predictionFieldValue = (
  predictions, { field, pathHigher, thresholds, indicatorMap, infoField, infoTitle },
) => {
  let value = predictions[field]
  if (value === null || value === undefined) {
    return { value }
  }

  const infoValue = predictions[infoField]

  if (thresholds) {
    value = parseFloat(value).toPrecision(3)
    const color = getPredictColor(value, pathHigher, thresholds)
    return { value, color, infoValue, infoTitle, pathHigher, thresholds }
  }

  return indicatorMap[value[0]] || indicatorMap[value]
}

const PATHOGENIC_COLORS = ['green', 'light green', 'grey', 'yellow', 'red', 'dark red']

const Prediction = (
  { field, fieldTitle, value, color, infoValue, infoTitle, pathHigher, thresholds, href },
) => {
  const indicator = infoValue ? (
    <Popup
      header={infoTitle}
      content={infoValue}
      trigger={<Icon name="question circle" size="small" color={color} />}
    />
  ) : <Icon name="circle" size="small" color={color} />
  const fieldName = fieldTitle || snakecaseToTitlecase(field)
  const fieldDisplay = thresholds ? (
    <Popup
      header={`${fieldName} Color Ranges`}
      content={
        <div>
          {thresholds.map((th, i) => {
            if (!th) {
              return null
            }
            const t = pathHigher ? th : -1 * th
            if (i < 3) {
              return <div>{`${PATHOGENIC_COLORS[i]} ${pathHigher ? '<' : '>'}= ${t}`}</div>
            }
            return <div>{`${PATHOGENIC_COLORS[i]} ${pathHigher ? '>' : '<'}= ${t}`}</div>
          }).filter(e => !!e)}
        </div>
      }
      trigger={<span>{fieldName}</span>}
    />
  ) : fieldName

  const valueDisplay = href ? <a href={href} target="_blank" rel="noreferrer">{value}</a> : value

  return (
    <div>
      {indicator}
      {fieldDisplay}
      <PredictionValue>{valueDisplay}</PredictionValue>
    </div>
  )
}

Prediction.propTypes = {
  field: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  infoValue: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  infoTitle: PropTypes.string,
  fieldTitle: PropTypes.string,
  color: PropTypes.string,
  pathHigher: PropTypes.bool,
  thresholds: PropTypes.arrayOf(PropTypes.number),
  href: PropTypes.string,
}

class Predictions extends React.PureComponent {

  static propTypes = {
    variant: PropTypes.object,
    gene: PropTypes.object,
  }

  state = { showMore: false }

  toggleShowMore = () => {
    this.setState(prevState => ({ showMore: !prevState.showMore }))
  }

  render() {
    const { variant, gene } = this.props
    const { predictions } = variant
    const { showMore } = this.state

    if (!predictions) {
      return null
    }

    const genePredictors = {}
    if (gene && gene.primateAi) {
      genePredictors.primate_ai = {
        field: 'primate_ai',
        pathHigher: gene.primateAi.percentile75 >= gene.primateAi.percentile25,
        thresholds: [null, null, gene.primateAi.percentile25, gene.primateAi.percentile75, null],
      }
    }

    const predictorFields = PREDICTOR_FIELDS.map(({ fieldTitle, getHref, ...predictorField }) => ({
      field: predictorField.field,
      fieldTitle,
      href: getHref && getHref(variant),
      ...predictionFieldValue(predictions, genePredictors[predictorField.field] || predictorField),
    })).filter(predictorField => predictorField.value !== null && predictorField.value !== undefined)
    return (
      <div>
        {
          predictorFields.slice(0, NUM_TO_SHOW_ABOVE_THE_FOLD).map(predictorField => (
            <Prediction key={predictorField.field} {...predictorField} />))
        }
        {predictorFields.length > NUM_TO_SHOW_ABOVE_THE_FOLD && (
          <Transition.Group animation="fade down" duration="500">
            {
              showMore && predictorFields.slice(NUM_TO_SHOW_ABOVE_THE_FOLD).map(predictorField => (
                <Prediction key={predictorField.field} {...predictorField} />
              ))
            }
            <ButtonLink onClick={this.toggleShowMore}>
              <HorizontalSpacer width={20} />
              {showMore ? 'hide' : 'show more...'}
            </ButtonLink>
          </Transition.Group>
        )}
      </div>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[getVariantMainGeneId(ownProps.variant)],
})

export default connect(mapStateToProps)(Predictions)
