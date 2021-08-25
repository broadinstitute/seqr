import React, { useState } from 'react'
import PropTypes from 'prop-types'
import { Table, Dropdown, Button, Message } from 'semantic-ui-react'
import AcmgRuleSpecification from './AcmgRuleSpecification'
import dropDownOptions from './AcmgCriteriaDropDownOptions'

const AcmgCriteria = (props) => {
  const { criteria, setCriteria, setActive } = props
  const { acmgCalculationValue, setAcmgCalculationValue } = props
  const { getScore, setScore } = props
  const [formWarning, setFormWarning] = useState('')

  const criteriaUsed = {}
  for (let i = 0; i < criteria.length; i++) {
    criteriaUsed[criteria[i]] = true
  }

  const addOrRemoveCriteria = (event, data) => {
    const values = data.value.split('_')
    const category = values[0]

    const value = `${values[1]}_${values[2]}`
    const answer = values[3]

    const fullCriteria = value
    const criteriaCopy = [...criteria]

    const acmgCalculationValueCopy = Object.assign({}, acmgCalculationValue)
    if (answer === 'No' && criteriaUsed[fullCriteria] === true) {
      acmgCalculationValueCopy[category] -= 1
      const filteredCriteria = criteriaCopy.filter(item => item !== fullCriteria)

      setCriteria(filteredCriteria)
      setAcmgCalculationValue(acmgCalculationValueCopy)
    } else if (answer === 'Yes' && (criteriaUsed[fullCriteria] === false || criteriaUsed[fullCriteria] === undefined)) {
      acmgCalculationValueCopy[category] += 1
      criteriaCopy.push(fullCriteria)

      setCriteria(criteriaCopy)
      setAcmgCalculationValue(acmgCalculationValueCopy)
    }

    setScore(getScore(acmgCalculationValueCopy))
  }

  const clearFields = () => {
    setAcmgCalculationValue({
      PVS: 0,
      PS: 0,
      PM: 0,
      PP: 0,
      BA: 0,
      BS: 0,
      BP: 0,
    })
    setCriteria([])
    setScore('Unknown')
  }

  const submitForm = () => {
    if (getScore(acmgCalculationValue) === 'Unknown') {
      setFormWarning('Please select at least one criteria from the table below.')
    } else if (getScore(acmgCalculationValue) === 'Conflicting') {
      setFormWarning('You have conflicting score. Please verify your selections.')
    } else {
      setFormWarning(false)
      setActive(false)
    }
  }

  const fontStyleSize = { fontSize: '13px' }
  const fontStyleWritingMode = { writingMode: 'sideways-lr', marginLeft: '-10px' }

  return (
    <div>
      {formWarning !== '' &&
        <Message warning>
          <Message.Header>Warning</Message.Header>
          <p>{formWarning}</p>
        </Message>
      }
      <Button primary onClick={submitForm}>Submit</Button>
      <Button onClick={clearFields} color="grey">Clear Form</Button>
      <Table celled structured textAlign="center" style={fontStyleSize}>
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell colSpan="1"></Table.HeaderCell>
            <Table.HeaderCell colSpan="2">Benign</Table.HeaderCell>
            <Table.HeaderCell colSpan="4">Pathogenic</Table.HeaderCell>
          </Table.Row>
        </Table.Header>

        <Table.Body>
          <Table.Row>
            <Table.Cell></Table.Cell>
            <Table.Cell width={2}>Strong</Table.Cell>
            <Table.Cell width={3}>Supporting</Table.Cell>
            <Table.Cell width={3}>Supporting</Table.Cell>
            <Table.Cell width={3}>Moderate</Table.Cell>
            <Table.Cell width={3}>Strong</Table.Cell>
            <Table.Cell width={3}>Very Strong</Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell rowSpan="3"><span style={fontStyleWritingMode}>Population Data</span></Table.Cell>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BA1_S</Table.Cell>
                    <Table.Cell width={2}>MAF too high<br />(Stand Alone)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BA1_S ? 'Y' : ''}
                        key="dropdown0"
                        placeholder="N"
                        options={dropDownOptions[0]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BA1_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM2_P</Table.Cell>
                    <Table.Cell width={2}>LOW AF in pop db</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM2_P ? 'Y' : ''}
                        key="dropdown1"
                        placeholder="N"
                        options={dropDownOptions[1]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM2_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM2_M</Table.Cell>
                    <Table.Cell width={2}>Absent (or rare) in<br />pop db with coverage<br />{'>20x'}</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM2_M ? 'Y' : ''}
                        key="dropdown2"
                        placeholder="N"
                        options={dropDownOptions[2]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM2_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BS1_S</Table.Cell>
                    <Table.Cell width={2}>MAF too high (Strong)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS1_S ? 'Y' : ''}
                        key="dropdown3"
                        placeholder="N"
                        options={dropDownOptions[3]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS1_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BS1_P</Table.Cell>
                    <Table.Cell width={2}>MAF too high (Supporting)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS1_P ? 'Y' : ''}
                        key="dropdown4"
                        placeholder="N"
                        options={dropDownOptions[4]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS1_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS4_P</Table.Cell>
                    <Table.Cell width={2}>Proband Count -<br />Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS4_P ? 'Y' : ''}
                        key="dropdown5"
                        placeholder="N"
                        options={dropDownOptions[5]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS4_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS4_M</Table.Cell>
                    <Table.Cell width={2}>Proband Count -<br />Moderate</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS4_M ? 'Y' : ''}
                        key="dropdown6"
                        placeholder="N"
                        options={dropDownOptions[6]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS4_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS4_S</Table.Cell>
                    <Table.Cell width={2}>Case-control OR<br />Proband Count</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS4_S ? 'Y' : ''}
                        key="dropdown7"
                        placeholder="N"
                        options={dropDownOptions[7]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS4_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BS2_S</Table.Cell>
                    <Table.Cell width={2}>Observ in unaffected</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS2_S ? 'Y' : ''}
                        key="dropdown8"
                        placeholder="N"
                        options={dropDownOptions[8]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS2_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BS2_P</Table.Cell>
                    <Table.Cell width={2}>BS2_Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS2_P ? 'Y' : ''}
                        key="dropdown9"
                        placeholder="N"
                        options={dropDownOptions[9]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS2_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell rowSpan="5"><span style={fontStyleWritingMode}>Computational and Predictive Data</span></Table.Cell>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP1_S</Table.Cell>
                    <Table.Cell width={2}>BP1_Strong</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP1_S ? 'Y' : ''}
                        key="dropdown10"
                        placeholder="N"
                        options={dropDownOptions[10]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP1_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP1_P</Table.Cell>
                    <Table.Cell width={2}>Truncating disease causing<br />variant missense</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP1_P ? 'Y' : ''}
                        key="dropdown11"
                        placeholder="N"
                        options={dropDownOptions[11]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP1_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS1_P</Table.Cell>
                    <Table.Cell width={2}>PS1_Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS1_P ? 'Y' : ''}
                        key="dropdown12"
                        placeholder="N"
                        options={dropDownOptions[12]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS1_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS1_M</Table.Cell>
                    <Table.Cell width={2}>PS1_Moderate</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS1_M ? 'Y' : ''}
                        key="dropdown13"
                        placeholder="N"
                        options={dropDownOptions[13]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS1_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS1_S</Table.Cell>
                    <Table.Cell width={2}>Same AA change as<br />establish pathogenic variant</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS1_S ? 'Y' : ''}
                        key="dropdown14"
                        placeholder="N"
                        options={dropDownOptions[14]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS1_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP3_S</Table.Cell>
                    <Table.Cell width={2}>BP3_Strong</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP3_S ? 'Y' : ''}
                        key="dropdown15"
                        placeholder="N"
                        options={dropDownOptions[15]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP3_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP3_P</Table.Cell>
                    <Table.Cell width={2}>In-frame indel in repeat<br />region w/out known function</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP3_P ? 'Y' : ''}
                        key="dropdown16"
                        placeholder="N"
                        options={dropDownOptions[16]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP3_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM5_P</Table.Cell>
                    <Table.Cell width={2}>PM5_Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM5_P ? 'Y' : ''}
                        key="dropdown17"
                        placeholder="N"
                        options={dropDownOptions[17]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM5_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM5_M</Table.Cell>
                    <Table.Cell width={2}>Diff pathogenic<br />missense variant at<br />codon</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM5_M ? 'Y' : ''}
                        key="dropdown18"
                        placeholder="N"
                        options={dropDownOptions[18]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM5_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM5_S</Table.Cell>
                    <Table.Cell width={2}>{'>=2 diff path'}<br />missense variants at<br />codon</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM5_S ? 'Y' : ''}
                        key="dropdown19"
                        placeholder="N"
                        options={dropDownOptions[19]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM5_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP4_S</Table.Cell>
                    <Table.Cell width={2}>Variant AA found<br />in {'>='} 3 mamals</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP4_S ? 'Y' : ''}
                        key="dropdown20"
                        placeholder="N"
                        options={dropDownOptions[20]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP4_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP4_P</Table.Cell>
                    <Table.Cell width={2}>Computational evidence<br />suggests no impact</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP4_P ? 'Y' : ''}
                        key="dropdown21"
                        placeholder="N"
                        options={dropDownOptions[21]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP4_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PSV1_P</Table.Cell>
                    <Table.Cell width={2}>PSV1_Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PSV1_P ? 'Y' : ''}
                        key="dropdown22"
                        placeholder="N"
                        options={dropDownOptions[22]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PSV1_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PVS1_M</Table.Cell>
                    <Table.Cell width={2}>Null variant -<br />Moderate</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PVS1_M ? 'Y' : ''}
                        key="dropdown23"
                        placeholder="N"
                        options={dropDownOptions[23]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PVS1_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PVS1_S</Table.Cell>
                    <Table.Cell width={2}>Null variant -<br />Strong</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PVS1_S ? 'Y' : ''}
                        key="dropdown24"
                        placeholder="N"
                        options={dropDownOptions[24]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PVS1_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PVS1_VS</Table.Cell>
                    <Table.Cell width={2}>Null variant & LOF<br />known mechanism</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PVS1_VS ? 'Y' : ''}
                        key="dropdown25"
                        placeholder="N"
                        options={dropDownOptions[25]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PVS1_VS ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PP3_P</Table.Cell>
                    <Table.Cell width={2}>Computation evidence<br />suggests impact</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP3_P ? 'Y' : ''}
                        key="dropdown26"
                        placeholder="N"
                        options={dropDownOptions[26]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP3_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PP3_M</Table.Cell>
                    <Table.Cell width={2}>PP3_Moderate</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP3_M ? 'Y' : ''}
                        key="dropdown27"
                        placeholder="N"
                        options={dropDownOptions[27]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP3_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP7_S</Table.Cell>
                    <Table.Cell width={2}>BP7_Strong</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP7_S ? 'Y' : ''}
                        key="dropdown28"
                        placeholder="N"
                        options={dropDownOptions[28]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP7_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP7_P</Table.Cell>
                    <Table.Cell width={2}>Silent or noncons splice<br />(see below) with no<br />predicted splice impact</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP7_P ? 'Y' : ''}
                        key="dropdown29"
                        placeholder="N"
                        options={dropDownOptions[29]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP7_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM4_S</Table.Cell>
                    <Table.Cell width={2}>In-frame indel of 1-2 AA</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM4_S ? 'Y' : ''}
                        key="dropdown30"
                        placeholder="N"
                        options={dropDownOptions[30]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM4_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM4_M</Table.Cell>
                    <Table.Cell width={2}>Protein length changing<br />{'(>2 AA)'} in non-<br />repeat region</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM4_M ? 'Y' : ''}
                        key="dropdown31"
                        placeholder="N"
                        options={dropDownOptions[31]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM4_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM4_S</Table.Cell>
                    <Table.Cell width={2}>PM4_Strong</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM4S_S ? 'Y' : ''}
                        key="dropdown32"
                        placeholder="N"
                        options={dropDownOptions[32]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM4S_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell rowSpan="3"><span style={fontStyleWritingMode}>Functional Data</span></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM1_P</Table.Cell>
                    <Table.Cell width={2}>PM1_Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM1_P ? 'Y' : ''}
                        key="dropdown33"
                        placeholder="N"
                        options={dropDownOptions[33]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM1_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM1_M</Table.Cell>
                    <Table.Cell width={2}>Mutation hotspot or<br />fxnl domain</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM1_M ? 'Y' : ''}
                        key="dropdown34"
                        placeholder="N"
                        options={dropDownOptions[34]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM1_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM1_S</Table.Cell>
                    <Table.Cell width={2}>PM1_Strong</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM1_S ? 'Y' : ''}
                        key="dropdown35"
                        placeholder="N"
                        options={dropDownOptions[35]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM1_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PP2_P</Table.Cell>
                    <Table.Cell width={2}>Missense in a gene with<br />low rate of benign<br />missense & path<br />missense common</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP2_P ? 'Y' : ''}
                        key="dropdown36"
                        placeholder="N"
                        options={dropDownOptions[36]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP2_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BS3_S</Table.Cell>
                    <Table.Cell width={2}>Established fxnl<br />study shows no<br />deleterious effect</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS3_S ? 'Y' : ''}
                        key="dropdown37"
                        placeholder="N"
                        options={dropDownOptions[37]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS3_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BS3_P</Table.Cell>
                    <Table.Cell width={2}>BS3_Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS3_P ? 'Y' : ''}
                        key="dropdown38"
                        placeholder="N"
                        options={dropDownOptions[38]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS3_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS3_P</Table.Cell>
                    <Table.Cell width={2}>Functional assay -<br />Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS3_P ? 'Y' : ''}
                        key="dropdown39"
                        placeholder="N"
                        options={dropDownOptions[39]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS3_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS3_M</Table.Cell>
                    <Table.Cell width={2}>Functional assay -<br />Moderate</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS3_M ? 'Y' : ''}
                        key="dropdown40"
                        placeholder="N"
                        options={dropDownOptions[40]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS3_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS3_S</Table.Cell>
                    <Table.Cell width={2}>Established fxnl<br />study shows<br />deleterious effect</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS3_S ? 'Y' : ''}
                        key="dropdown41"
                        placeholder="N"
                        options={dropDownOptions[41]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS3_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell><span style={fontStyleWritingMode}>Segregation Data</span></Table.Cell>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BS4_S</Table.Cell>
                    <Table.Cell width={2}>Lack of<br />segregation in<br />affected</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS4_S ? 'Y' : ''}
                        key="dropdown42"
                        placeholder="N"
                        options={dropDownOptions[42]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS4_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BS4_P</Table.Cell>
                    <Table.Cell width={2}>BS4_Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS4_P ? 'Y' : ''}
                        key="dropdown43"
                        placeholder="N"
                        options={dropDownOptions[43]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS4_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PP1_P</Table.Cell>
                    <Table.Cell width={2}>Coseg with disease<br />Dominant: 3 segs<br />Recessive:</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP1_P ? 'Y' : ''}
                        key="dropdown44"
                        placeholder="N"
                        options={dropDownOptions[44]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP1_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PP1_M</Table.Cell>
                    <Table.Cell width={2}>Coseg with disease<br />Dominant: 5 segs<br />Recessive:</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP1_M ? 'Y' : ''}
                        key="dropdown45"
                        placeholder="N"
                        options={dropDownOptions[45]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP1_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PP1_S</Table.Cell>
                    <Table.Cell width={2}>Coseg with disease<br />Dominant: 7 segs<br />Recessive</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP1_S ? 'Y' : ''}
                        key="dropdown46"
                        placeholder="N"
                        options={dropDownOptions[46]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP1_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell rowSpan="2"><span style={fontStyleWritingMode}>De Novo Data</span></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM6_P</Table.Cell>
                    <Table.Cell width={2}>PM6_Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM6_P ? 'Y' : ''}
                        key="dropdown47"
                        placeholder="N"
                        options={dropDownOptions[47]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM6_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM6_M</Table.Cell>
                    <Table.Cell width={2}>De novo (neither<br />paternity or maternity<br />confirmed)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM6_M ? 'Y' : ''}
                        key="dropdown48"
                        placeholder="N"
                        options={dropDownOptions[48]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM6_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM6_S</Table.Cell>
                    <Table.Cell width={2}>{'>=2'} independent<br />occurences of PM6</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM6_S ? 'Y' : ''}
                        key="dropdown49"
                        placeholder="N"
                        options={dropDownOptions[49]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM6_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS2_P</Table.Cell>
                    <Table.Cell width={2}>PS2_Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS2_P ? 'Y' : ''}
                        key="dropdown50"
                        placeholder="N"
                        options={dropDownOptions[50]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS2_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS2_M</Table.Cell>
                    <Table.Cell width={2}>PS2_Moderate</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS2_M ? 'Y' : ''}
                        key="dropdown51"
                        placeholder="N"
                        options={dropDownOptions[51]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS2_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS2_S</Table.Cell>
                    <Table.Cell width={2}>De novo (paternity<br />and maternity<br />confirmed)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS2_S ? 'Y' : ''}
                        key="dropdown52"
                        placeholder="N"
                        options={dropDownOptions[52]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS2_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS2_VS</Table.Cell>
                    <Table.Cell width={2}>{'>=2'} independent<br />occurences of PS2</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS2_VS ? 'Y' : ''}
                        key="dropdown53"
                        placeholder="N"
                        options={dropDownOptions[53]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS2_VS ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell><span style={fontStyleWritingMode}>Alleleic Data</span></Table.Cell>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP2_S</Table.Cell>
                    <Table.Cell width={2}>Met, BP2_Strong</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP2_S ? 'Y' : ''}
                        key="dropdown54"
                        placeholder="N"
                        options={dropDownOptions[54]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP2_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP2_P</Table.Cell>
                    <Table.Cell width={2}>Observed in trans with<br />dominant variant OR<br />observed in cis with<br />path variant</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP2_P ? 'Y' : ''}
                        key="dropdown55"
                        placeholder="N"
                        options={dropDownOptions[55]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP2_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM3_P</Table.Cell>
                    <Table.Cell width={2}>Variant in trans does<br />not meet LP/P criteria</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM3_P ? 'Y' : ''}
                        key="dropdown56"
                        placeholder="N"
                        options={dropDownOptions[56]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM3_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM3_M</Table.Cell>
                    <Table.Cell width={2}>Detected in trans with<br />P/LP variant<br />(recessive disorders)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM3_M ? 'Y' : ''}
                        key="dropdown57"
                        placeholder="N"
                        options={dropDownOptions[57]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM3_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM3_S</Table.Cell>
                    <Table.Cell width={2}>2-3 occurences of<br />PM3 (see below)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM3_S ? 'Y' : ''}
                        key="dropdown58"
                        placeholder="N"
                        options={dropDownOptions[58]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM3_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM3_VS</Table.Cell>
                    <Table.Cell width={2}>{'>=4'} occurences of<br />PM3 (see below)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM3_VS ? 'Y' : ''}
                        key="dropdown59"
                        placeholder="N"
                        options={dropDownOptions[59]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM3_VS ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell><span style={fontStyleWritingMode}>Other data</span></Table.Cell>
            <Table.Cell>
              <Table size="small" color="pink">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PB5_S</Table.Cell>
                    <Table.Cell width={2}>Met, PB5_Strong</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PB5_S ? 'Y' : ''}
                        key="dropdown60"
                        placeholder="N"
                        options={dropDownOptions[60]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PB5_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP5_P</Table.Cell>
                    <Table.Cell width={2}>Found in case with an<br />alternative cause</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP5_P ? 'Y' : ''}
                        key="dropdown61"
                        placeholder="N"
                        options={dropDownOptions[61]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP5_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PP4_P</Table.Cell>
                    <Table.Cell width={2}>Patient phenotype or<br />FH high specific for<br />gene</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP4_P ? 'Y' : ''}
                        key="dropdown62"
                        placeholder="N"
                        options={dropDownOptions[62]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP4_P ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PP4_M</Table.Cell>
                    <Table.Cell width={2}>PP4_Moderate</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP4_M ? 'Y' : ''}
                        key="dropdown63"
                        placeholder="N"
                        options={dropDownOptions[63]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP4_M ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PP4_S</Table.Cell>
                    <Table.Cell width={2}>PP4_Strong</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP4_S ? 'Y' : ''}
                        key="dropdown64"
                        placeholder="N"
                        options={dropDownOptions[64]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP4_S ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>
      <br />
      <AcmgRuleSpecification />
    </div>
  )
}

AcmgCriteria.propTypes = {
  criteria: PropTypes.array.isRequired,
  setCriteria: PropTypes.func.isRequired,
  acmgCalculationValue: PropTypes.object.isRequired,
  setAcmgCalculationValue: PropTypes.func.isRequired,
  getScore: PropTypes.func.isRequired,
  setScore: PropTypes.func.isRequired,
  setActive: PropTypes.func.isRequired,
}

export default AcmgCriteria
