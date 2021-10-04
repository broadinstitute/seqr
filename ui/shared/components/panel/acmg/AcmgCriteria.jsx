import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Table, Dropdown, Button, Message } from 'semantic-ui-react'
import AcmgRuleSpecification from './AcmgRuleSpecification'
import ACMG_DROP_DOWN_OPTIONS from './AcmgCriteriaDropDownOptions'
import CATEGORY_CRITERIA_SCORE from './AcmgCategoryCriteriaScore'
import { updateVariantClassification } from '../../../../redux/rootReducer'

const FONT_STYLE_WRITING_MODE = { writingMode: 'sideways-lr', marginLeft: '-10px' }
const TABLE_ROW_TOTAL_COLUMNS = 6
const TABLE_COLUMN_COLOR = ['pink', 'blue', 'green', 'orange', 'red', 'red']

export const getNewScoreValue = (criteria) => {
  let newScore = 0
  criteria.forEach((item) => {
    newScore += CATEGORY_CRITERIA_SCORE[item]
  })
  return newScore
}

class AcmgCriteria extends React.PureComponent {
  constructor(props) {
    super(props)

    this.state = {
      formWarning: '',
    }
  }

  setFormWarning(warning) {
    this.setState({
      formWarning: warning,
    })
  }

  getCriteriaUsed() {
    const criteriaUsed = {}
    for (let i = 0; i < this.props.criteria.length; i++) {
      criteriaUsed[this.props.criteria[i]] = true
    }

    return criteriaUsed
  }

  addOrRemoveCriteria = (_, data) => {
    const values = data.value.split('_')

    const value = `${values[1]}_${values[2]}`
    const answer = values[3]

    const fullCriteria = value
    const criteriaCopy = [...this.props.criteria]

    const criteriaUsed = this.getCriteriaUsed()

    if (answer === 'No' && criteriaUsed[fullCriteria] === true) {
      const filteredCriteria = criteriaCopy.filter(item => item !== fullCriteria)
      this.props.setCriteria(filteredCriteria)
    } else if (answer === 'Yes' && (criteriaUsed[fullCriteria] === false || criteriaUsed[fullCriteria] === undefined)) {
      criteriaCopy.push(fullCriteria)
      this.props.setCriteria(criteriaCopy)
    }
  }

  clearFields = () => {
    this.props.setCriteria([])
    this.props.setAcmgClassification('Unknown')
  }

  submitForm = () => {
    if (this.props.acmgClassification === 'Unknown') {
      this.setFormWarning('Please select at least one criteria from the table below.')
    } else if (this.props.acmgClassification === 'Conflicting') {
      this.setFormWarning('You have conflicting score. Please verify your selections.')
    } else {
      this.setFormWarning(false)
      this.props.setActive(false)
      this.props.variant.acmgClassification = {
        score: getNewScoreValue(this.props.criteria),
        classify: this.props.acmgClassification,
        criteria: this.props.criteria,
      }
      this.props.dispatchUpdateVariantClassification()
    }
  }

  getTableRows = () => {
    return ACMG_DROP_DOWN_OPTIONS.map((dropDownOption) => {
      let startArray = 0
      let endArray = TABLE_ROW_TOTAL_COLUMNS
      const rows = []

      while (startArray !== dropDownOption.options.length) {
        const row = dropDownOption.options.slice(startArray, endArray)
        rows.push(row)

        startArray = endArray
        endArray += TABLE_ROW_TOTAL_COLUMNS
      }

      const elements = rows.map((row, rowIdx) => {
        const criteriaUsed = this.getCriteriaUsed()
        return (
          <Table.Row>
            { rowIdx === 0 ? <Table.Cell rowSpan={dropDownOption.optionRowSpan}><span style={FONT_STYLE_WRITING_MODE}>{dropDownOption.optionTitle}</span></Table.Cell> : null }
            { row.map((cell, cellIdx) => {
              if (cell.length === 0) {
                return <Table.Cell />
              }
              const color = TABLE_COLUMN_COLOR[cellIdx % TABLE_ROW_TOTAL_COLUMNS]
              const option = cell[0]

              return (
                <Table.Cell>
                  <Table size="small" color={color}>
                    <Table.Body>
                      <Table.Row textAlign="center" key={`table-row-${option.description}`}>
                        <Table.Cell width={1}>{option.key}</Table.Cell>
                        <Table.Cell width={2}>{option.description}</Table.Cell>
                        <Table.Cell width={1}>
                          <Dropdown
                            value={option.key ? 'Y' : ''}
                            key={`dropdown-${option.key}`}
                            options={option.values}
                            onChange={this.addOrRemoveCriteria}
                            text={criteriaUsed[option.key] ? 'Y' : 'N'}
                          />
                        </Table.Cell>
                      </Table.Row>
                    </Table.Body>
                  </Table>
                </Table.Cell>
              )
          })}
          </Table.Row>
        )
      })

      return elements
    })
  }

  getNewScore = (criteria) => {
    const newScore = getNewScoreValue(criteria)
    if (newScore >= 10) {
      return 'Pathogenic'
    } else if (newScore >= 6 && newScore <= 9) {
      return 'Likely Pathogenic'
    } else if (newScore >= 0 && newScore <= 5) {
      return 'Uncertain'
    } else if (newScore >= -6 && newScore <= -1) {
      return 'Likely Benign'
    }
    return 'Benign'
  }

  render() {
    if (this.props.criteria.length > 0) {
      this.props.setAcmgClassification(this.getNewScore(this.props.criteria))
    }

    return (
      <div>
        {this.state.formWarning !== '' &&
          <Message warning>
            <Message.Header>Warning</Message.Header>
            <p>{this.state.formWarning}</p>
          </Message>
        }
        <Button primary onClick={this.submitForm}>Submit</Button>
        <Button onClick={this.clearFields} color="grey">Clear Form</Button>
        <Table celled structured textAlign="center">
          <Table.Header>
            <Table.Row key="table-row-headercell">
              <Table.HeaderCell colSpan="1"></Table.HeaderCell>
              <Table.HeaderCell colSpan="2">Benign</Table.HeaderCell>
              <Table.HeaderCell colSpan="4">Pathogenic</Table.HeaderCell>
            </Table.Row>
          </Table.Header>

          <Table.Body>
            <Table.Row key="table-row-headers">
              <Table.Cell></Table.Cell>
              <Table.Cell width={2}>Strong</Table.Cell>
              <Table.Cell width={3}>Supporting</Table.Cell>
              <Table.Cell width={3}>Supporting</Table.Cell>
              <Table.Cell width={3}>Moderate</Table.Cell>
              <Table.Cell width={3}>Strong</Table.Cell>
              <Table.Cell width={3}>Very Strong</Table.Cell>
            </Table.Row>

            { this.getTableRows().map(rows => rows.map(row => row)) }
          </Table.Body>
        </Table>
        <br />
        <AcmgRuleSpecification />
      </div>
    )
  }
}

AcmgCriteria.propTypes = {
  criteria: PropTypes.array.isRequired,
  setCriteria: PropTypes.func.isRequired,
  acmgClassification: PropTypes.string.isRequired,
  setAcmgClassification: PropTypes.func.isRequired,
  setActive: PropTypes.func.isRequired,
  variant: PropTypes.object.isRequired,
  dispatchUpdateVariantClassification: PropTypes.func,
}

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    dispatchUpdateVariantClassification: (updates) => {
      dispatch(updateVariantClassification({ ...updates, variant: ownProps.variant }))
    },
  }
}

export default connect(null, mapDispatchToProps)(AcmgCriteria)
