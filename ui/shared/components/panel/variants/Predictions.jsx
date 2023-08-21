import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Icon, Transition, Popup } from 'semantic-ui-react'

import { getGenesById } from 'redux/selectors'
import { PREDICTOR_FIELDS, PRED_COLOR_MAP, getVariantMainGeneId } from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import { HorizontalSpacer } from '../../Spacers'
import { ButtonLink, ColoredIcon } from '../../StyledComponents'

const PredictionValue = styled.span`
  margin-left: 5px;
  font-weight: bolder;
  color: black;
  text-transform: uppercase;
`

const NUM_TO_SHOW_ABOVE_THE_FOLD = 6 // how many predictors to show immediately

const predictionFieldValue = (
  predictions, { field, thresholds, indicatorMap, infoField, infoTitle },
) => {
  let value = predictions[field]
  if (value === null || value === undefined) {
    return { value }
  }

  const infoValue = predictions[infoField]

  if (thresholds) {
    value = parseFloat(value).toPrecision(3)
    const color = PRED_COLOR_MAP.find(
      (clr, i) => (thresholds[i - 1] || thresholds[i]) &&
        (thresholds[i - 1] === undefined || value >= thresholds[i - 1]) &&
        (thresholds[i] === undefined || value < thresholds[i]),
    )
    return { value, color, infoValue, infoTitle, thresholds }
  }

  return indicatorMap[value[0]] || indicatorMap[value]
}

const coloredIcon = color => React.createElement(color.startsWith('#') ? ColoredIcon : Icon, { name: 'circle', size: 'small', color })

const Prediction = (
  { field, fieldTitle, value, color, infoValue, infoTitle, thresholds, href },
) => {
  const indicator = infoValue ? (
    <Popup
      header={infoTitle}
      content={infoValue}
      trigger={<Icon name="question circle" size="small" color={color} />}
    />
  ) : coloredIcon(color)
  const fieldName = fieldTitle || snakecaseToTitlecase(field)
  const fieldDisplay = thresholds ? (
    <Popup
      header={`${fieldName} Color Ranges`}
      content={
        PRED_COLOR_MAP.map((c, i) => {
          if (thresholds[i] === undefined && thresholds[i - 1] === undefined) {
            return null
          }
          return (
            <div key={c}>
              {coloredIcon(c)}
              {thresholds[i] === undefined ? ` >= ${thresholds[i - 1]}` : ` < ${thresholds[i]}`}
            </div>
          )
        })
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
        thresholds: [undefined, undefined, gene.primateAi.percentile25.toPrecision(3),
          gene.primateAi.percentile75.toPrecision(3), undefined],
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
