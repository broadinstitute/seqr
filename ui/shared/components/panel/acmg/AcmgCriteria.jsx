import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Table, Dropdown, Button, Message } from 'semantic-ui-react'

import { updateVariantClassification } from 'redux/rootReducer'
import { closeModal } from 'redux/utils/modalReducer'
import AcmgRuleSpecification from './AcmgRuleSpecification'
import ACMG_DROP_DOWN_OPTIONS from './AcmgCriteriaDropDownOptions'
import CATEGORY_CRITERIA_SCORE from './AcmgCategoryCriteriaScore'

const FONT_STYLE_WRITING_MODE = { writingMode: 'sideways-lr', marginLeft: '-10px' }
const TABLE_ROW_TOTAL_COLUMNS = 6
const TABLE_COLUMN_COLOR = ['pink', 'blue', 'green', 'orange', 'red', 'red']
const CATEGORY_CONFIGS = [
  { classification: 'Pathogenic', isThisClassification: value => value >= 10 },
  { classification: 'Likely Pathogenic', isThisClassification: value => value >= 6 && value <= 9 },
  { classification: 'Uncertain', isThisClassification: value => value >= 0 && value <= 5 },
  { classification: 'Likely Benign', isThisClassification: value => value >= -6 && value <= -1 },
]

const formatCriteria = (criteria) => {
  const formattedCriteria = []
  criteria.forEach((c, criteriaIdx) => {
    formattedCriteria.push(c)

    if (criteriaIdx !== criteria.length - 1) {
      formattedCriteria[criteriaIdx] += ', '
    }
  })

  return formattedCriteria
}

export const getNewScoreValue = (criteria) => {
  let newScore = 0
  criteria.forEach((item) => {
    newScore += CATEGORY_CRITERIA_SCORE[item]
  })

  return newScore
}

class AcmgCriteria extends React.PureComponent {

  static propTypes = {
    setInactive: PropTypes.func.isRequired,
    variant: PropTypes.object.isRequired,
    dispatchUpdateVariantClassification: PropTypes.func,
  }

  constructor(props) {
    super(props)

    const { variant } = this.props
    const { classify = 'Unknown', criteria = [] } = variant.acmgClassification || {}
    // eslint-disable-next-line react/state-in-constructor
    this.state = { formWarning: '', criteria, classify, score: getNewScoreValue(criteria) }
  }

  setCriteria(criteria) {
    if (criteria.length > 0) {
      const score = getNewScoreValue(criteria)
      const newCategory = CATEGORY_CONFIGS.find(
        category => category.isThisClassification(score) === true,
      )
      const classify = newCategory ? newCategory.classification : 'Benign'
      this.setState({ criteria, score, classify })
    } else {
      this.clearFields()
    }
  }

  setFormWarning(warning) {
    this.setState({
      formWarning: warning,
    })
  }

  getCriteriaUsed() {
    const criteriaUsed = {}
    const { criteria } = this.state
    criteria.forEach((c) => {
      criteriaUsed[c] = true
    })

    return criteriaUsed
  }

  addOrRemoveCriteria = (_, data) => {
    const values = data.value.split('_')

    const value = `${values[1]}_${values[2]}`
    const answer = values[3]

    const fullCriteria = value
    const { criteria } = this.state

    const criteriaUsed = this.getCriteriaUsed()

    if (answer === 'No' && criteriaUsed[fullCriteria] === true) {
      const filteredCriteria = criteria.filter(item => item !== fullCriteria)
      this.setCriteria(filteredCriteria)
    } else if (answer === 'Yes' && (criteriaUsed[fullCriteria] === false || criteriaUsed[fullCriteria] === undefined)) {
      this.setCriteria([...criteria, fullCriteria])
    }
  }

  clearFields = () => {
    this.setState({
      criteria: [],
      score: 0,
      classify: 'Unknown',
    })
  }

  submitForm = () => {
    const { setInactive, dispatchUpdateVariantClassification } = this.props
    const { classify, criteria, score } = this.state
    if (!classify || classify === 'Unknown') {
      this.setFormWarning('Please select at least one criteria from the table below.')
    } else if (classify === 'Conflicting') {
      this.setFormWarning('You have conflicting score. Please verify your selections.')
    } else {
      this.setFormWarning(false)
      setInactive()
      dispatchUpdateVariantClassification({ score, classify, criteria })
    }
  }

  getTableRows = () => {
    const dropDownRowns = ACMG_DROP_DOWN_OPTIONS.map((dropDownOption) => {
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
          // eslint-disable-next-line react/no-array-index-key
          <Table.Row key={rowIdx}>
            {rowIdx === 0 ?
              (
                <Table.Cell rowSpan={dropDownOption.optionRowSpan}>
                  <span style={FONT_STYLE_WRITING_MODE}>{dropDownOption.optionTitle}</span>
                </Table.Cell>
              ) : null}
            {row.map((cell, cellIdx) => {
              if (cell.length === 0) {
                // eslint-disable-next-line react/no-array-index-key
                return <Table.Cell key={cellIdx} />
              }
              const color = TABLE_COLUMN_COLOR[cellIdx % TABLE_ROW_TOTAL_COLUMNS]
              const option = cell[0]

              return (
                <Table.Cell key={option.key}>
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

    return dropDownRowns
  }

  render() {
    const { score, criteria, classify } = this.state
    const { formWarning } = this.state

    return (
      <div>
        <Table celled padded>
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell singleLine>Score</Table.HeaderCell>
              <Table.HeaderCell singleLine>Classification</Table.HeaderCell>
              <Table.HeaderCell>Criteria Applied</Table.HeaderCell>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            <Table.Row>
              <Table.Cell width="1">{score}</Table.Cell>
              <Table.Cell width="3">{classify}</Table.Cell>
              <Table.Cell>{criteria.length === 0 ? 'No criteria applied' : formatCriteria(criteria)}</Table.Cell>
            </Table.Row>
          </Table.Body>
        </Table>
        <br />
        {formWarning !== '' &&
          (
            <Message warning>
              <Message.Header>Warning</Message.Header>
              <p>{formWarning}</p>
            </Message>
          )}
        <Button primary onClick={this.submitForm}>Submit</Button>
        <Button onClick={this.clearFields} color="grey">Clear Form</Button>
        <Table celled structured textAlign="center">
          <Table.Header>
            <Table.Row key="table-row-headercell">
              <Table.HeaderCell colSpan="1" />
              <Table.HeaderCell colSpan="2">Benign</Table.HeaderCell>
              <Table.HeaderCell colSpan="4">Pathogenic</Table.HeaderCell>
            </Table.Row>
          </Table.Header>

          <Table.Body>
            <Table.Row key="table-row-headers">
              <Table.Cell />
              <Table.Cell width={2}>Strong</Table.Cell>
              <Table.Cell width={3}>Supporting</Table.Cell>
              <Table.Cell width={3}>Supporting</Table.Cell>
              <Table.Cell width={3}>Moderate</Table.Cell>
              <Table.Cell width={3}>Strong</Table.Cell>
              <Table.Cell width={3}>Very Strong</Table.Cell>
            </Table.Row>

            {this.getTableRows().map(rows => rows.map(row => row))}
          </Table.Body>
        </Table>
        <br />
        <AcmgRuleSpecification />
      </div>
    )
  }

}

const mapDispatchToProps = (dispatch, ownProps) => ({
  setInactive: () => dispatch(closeModal(ownProps.modalName)),
  dispatchUpdateVariantClassification: (acmgClassification) => {
    dispatch(updateVariantClassification(
      { variant: { ...ownProps.variant, acmgClassification }, familyGuid: ownProps.familyGuid },
    ))
  },
})

export default connect(null, mapDispatchToProps)(AcmgCriteria)
