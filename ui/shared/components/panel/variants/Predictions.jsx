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

const MORE_PREDICTORS = [
  'polyphen', 'sift', 'mut_taster', 'fathmm', 'metasvm', 'gerp_rs', 'phastcons100vert',
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

    return annotation ?
      <div>
        <Prediction field="cadd_phred" annotation={annotation} dangerThreshold={20} warningThreshold={10} name="CADD" />
        <Prediction field="dann_score" annotation={annotation} dangerThreshold={0.96} warningThreshold={0.93} name="DANN" />
        <Prediction field="revel_score" annotation={annotation} dangerThreshold={0.75} warningThreshold={0.5} name="REVEL" />
        <Prediction field="eigen_phred" annotation={annotation} dangerThreshold={1} warningThreshold={2}name="EIGEN" />
        <Prediction field="mpc_score" annotation={annotation} dangerThreshold={2} warningThreshold={1} name="MPC" />
        <Prediction field="primate_ai_score" annotation={annotation} dangerThreshold={0.7} warningThreshold={0.5} name="PMT AI" />
        <Transition.Group animation="fade down" duration="500">
          {
            this.state.showMore ?
              <div>
                {
                  MORE_PREDICTORS.map(field => <Prediction key={field} field={field} annotation={annotation} />)
                }
                <LinkButton onClick={() => this.setState({ showMore: false })}>hide</LinkButton>
              </div>
            :
              MORE_PREDICTORS.some(field => annotation[field] != null) &&
              <LinkButton onClick={() => this.setState({ showMore: true })}>show more..</LinkButton>
            }
        </Transition.Group>
      </div>
      : null
  }
}

