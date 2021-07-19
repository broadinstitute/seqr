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

    let value = values[1]
    const answer = values[2]

    // Supporting keys have dash (-) in their name. It is used to add more information and have unique key as well.
    if (value.includes('-')) {
      const splitValues = value.split('-')
      const key = splitValues[0]
      const text = splitValues[2]
      value = `${key}_${text}`
    }

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
                    <Table.Cell width={1}>BA1</Table.Cell>
                    <Table.Cell width={2}>MAF too high<br />(Stand Alone)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BA1 ? 'Y' : ''}
                        key="dropdown0"
                        placeholder="N"
                        options={dropDownOptions[0]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BA1 ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM2</Table.Cell>
                    <Table.Cell width={2}>Absent (or rare) in<br />pop db with coverage<br />{'>20x'}</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM2 ? 'Y' : ''}
                        key="dropdown1"
                        placeholder="N"
                        options={dropDownOptions[1]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM2 ? 'Y' : ''}
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
                    <Table.Cell width={1}>BS1</Table.Cell>
                    <Table.Cell width={2}>MAF too high</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS1 ? 'Y' : ''}
                        key="dropdown2"
                        placeholder="N"
                        options={dropDownOptions[2]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS1 ? 'Y' : ''}
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
                    <Table.Cell width={1}>PS4_P</Table.Cell>
                    <Table.Cell width={2}>Proband Count -<br />Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS4_Supporting ? 'Y' : ''}
                        key="dropdown3"
                        placeholder="N"
                        options={dropDownOptions[3]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS4_Supporting ? 'Y' : ''}
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
                        value={criteriaUsed.PS4_Moderate ? 'Y' : ''}
                        key="dropdown4"
                        placeholder="N"
                        options={dropDownOptions[4]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS4_Moderate ? 'Y' : ''}
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
                    <Table.Cell width={1}>PS4</Table.Cell>
                    <Table.Cell width={2}>Case-control OR<br />Proband Count</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS4 ? 'Y' : ''}
                        key="dropdown5"
                        placeholder="N"
                        options={dropDownOptions[5]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS4 ? 'Y' : ''}
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
                    <Table.Cell width={1}>BS2</Table.Cell>
                    <Table.Cell width={2}>Observ in unaffected</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS2 ? 'Y' : ''}
                        key="dropdown6"
                        placeholder="N"
                        options={dropDownOptions[6]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS2 ? 'Y' : ''}
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
            <Table.Cell></Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell rowSpan="4"><span style={fontStyleWritingMode}>Computational and Predictive Data</span></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP1</Table.Cell>
                    <Table.Cell width={2}>Truncating disease causing<br />variant missense</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP1 ? 'Y' : ''}
                        key="dropdown7"
                        placeholder="N"
                        options={dropDownOptions[7]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP1 ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS1</Table.Cell>
                    <Table.Cell width={2}>Same AA change as<br />establish pathogenic variant</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS1 ? 'Y' : ''}
                        key="dropdown8"
                        placeholder="N"
                        options={dropDownOptions[8]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS1 ? 'Y' : ''}
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
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP3</Table.Cell>
                    <Table.Cell width={2}>In-frame indel in repeat<br />region w/out known function</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP3 ? 'Y' : ''}
                        key="dropdown9"
                        placeholder="N"
                        options={dropDownOptions[9]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP3 ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM5</Table.Cell>
                    <Table.Cell width={2}>Diff pathogenic<br />missense variant at<br />codon</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM5 ? 'Y' : ''}
                        key="dropdown10"
                        placeholder="N"
                        options={dropDownOptions[10]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM5 ? 'Y' : ''}
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
                        value={criteriaUsed.PM5_Strong ? 'Y' : ''}
                        key="dropdown11"
                        placeholder="N"
                        options={dropDownOptions[11]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM5_Strong ? 'Y' : ''}
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
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP4</Table.Cell>
                    <Table.Cell width={2}>Computational evidence<br />suggests no impact</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP4 ? 'Y' : ''}
                        key="dropdown12"
                        placeholder="N"
                        options={dropDownOptions[12]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP4 ? 'Y' : ''}
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
                    <Table.Cell width={1}>PP3</Table.Cell>
                    <Table.Cell width={2}>Computational<br />evidente suggests<br />impact</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP3 ? 'Y' : ''}
                        key="dropdown13"
                        placeholder="N"
                        options={dropDownOptions[13]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP3 ? 'Y' : ''}
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
                        value={criteriaUsed.PVS1_Moderate ? 'Y' : ''}
                        key="dropdown14"
                        placeholder="N"
                        options={dropDownOptions[14]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PVS1_Moderate ? 'Y' : ''}
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
                        value={criteriaUsed.PVS1_Strong ? 'Y' : ''}
                        key="dropdown15"
                        placeholder="N"
                        options={dropDownOptions[15]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PVS1_Strong ? 'Y' : ''}
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
                    <Table.Cell width={1}>PVS1</Table.Cell>
                    <Table.Cell width={2}>Null variant & LOF<br />known mechanism</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PVS1 ? 'Y' : ''}
                        key="dropdown16"
                        placeholder="N"
                        options={dropDownOptions[16]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PVS1 ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP7</Table.Cell>
                    <Table.Cell width={2}>Silent or noncons splice<br />(see below) with no<br />predicted splice impact</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP7 ? 'Y' : ''}
                        key="dropdown17"
                        placeholder="N"
                        options={dropDownOptions[17]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP7 ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM4</Table.Cell>
                    <Table.Cell width={2}>Pritein length<br />changing variant{'>2'}<br />AA) in non-repeat<br />region</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM4 ? 'Y' : ''}
                        key="dropdown18"
                        placeholder="N"
                        options={dropDownOptions[18]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM4 ? 'Y' : ''}
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
            <Table.Cell rowSpan="2"><span style={fontStyleWritingMode}>Functional Data</span></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="green">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PP2</Table.Cell>
                    <Table.Cell width={2}>Missense in a gene<br />with low rate of<br />benign missense &<br />path missense<br />common</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP2 ? 'Y' : ''}
                        key="dropdown19"
                        placeholder="N"
                        options={dropDownOptions[19]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP2 ? 'Y' : ''}
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
                    <Table.Cell width={1}>PM1</Table.Cell>
                    <Table.Cell width={2}>Mutation hotspot or<br />fxnl domain</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM1 ? 'Y' : ''}
                        key="dropdown20"
                        placeholder="N"
                        options={dropDownOptions[20]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM1 ? 'Y' : ''}
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
                    <Table.Cell width={1}>BS3</Table.Cell>
                    <Table.Cell width={2}>Established fxnl<br />study shows no<br />deleterious effect</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS3 ? 'Y' : ''}
                        key="dropdown21"
                        placeholder="N"
                        options={dropDownOptions[21]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS3 ? 'Y' : ''}
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
                    <Table.Cell width={1}>PS3_P</Table.Cell>
                    <Table.Cell width={2}>Functional assay -<br />Supporting</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS3_Supporting ? 'Y' : ''}
                        key="dropdown22"
                        placeholder="N"
                        options={dropDownOptions[22]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS3_Supporting ? 'Y' : ''}
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
                        value={criteriaUsed.PS3_Moderate ? 'Y' : ''}
                        key="dropdown23"
                        placeholder="N"
                        options={dropDownOptions[23]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS3_Moderate ? 'Y' : ''}
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
                    <Table.Cell width={1}>PS3</Table.Cell>
                    <Table.Cell width={2}>Established fxnl<br />study shows<br />deleterious effect</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS3 ? 'Y' : ''}
                        key="dropdown24"
                        placeholder="N"
                        options={dropDownOptions[24]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS3 ? 'Y' : ''}
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
                    <Table.Cell width={1}>BS4</Table.Cell>
                    <Table.Cell width={2}>Lack of<br />segregation in<br />affected</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BS4 ? 'Y' : ''}
                        key="dropdown25"
                        placeholder="N"
                        options={dropDownOptions[25]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BS4 ? 'Y' : ''}
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
                    <Table.Cell width={1}>PP1</Table.Cell>
                    <Table.Cell width={2}>Coseg with disease<br />Dominant: 3 segs<br />Recessive:</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PP1 ? 'Y' : ''}
                        key="dropdown26"
                        placeholder="N"
                        options={dropDownOptions[26]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP1 ? 'Y' : ''}
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
                        value={criteriaUsed.PP1_Moderate ? 'Y' : ''}
                        key="dropdown27"
                        placeholder="N"
                        options={dropDownOptions[27]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP1_Moderate ? 'Y' : ''}
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
                        value={criteriaUsed.PP1_Strong ? 'Y' : ''}
                        key="dropdown28"
                        placeholder="N"
                        options={dropDownOptions[28]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PP1_Strong ? 'Y' : ''}
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
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM6</Table.Cell>
                    <Table.Cell width={2}>De novo (neither<br />paternity or maternity<br />confirmed)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM6 ? 'Y' : ''}
                        key="dropdown29"
                        placeholder="N"
                        options={dropDownOptions[29]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM6 ? 'Y' : ''}
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
                        value={criteriaUsed.PM6_Strong ? 'Y' : ''}
                        key="dropdown30"
                        placeholder="N"
                        options={dropDownOptions[30]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM6_Strong ? 'Y' : ''}
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
            <Table.Cell></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="red">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PS2</Table.Cell>
                    <Table.Cell width={2}>De novo (paternity<br />and maternity<br />confirmed)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PS2 ? 'Y' : ''}
                        key="dropdown31"
                        placeholder="N"
                        options={dropDownOptions[31]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS2 ? 'Y' : ''}
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
                        value={criteriaUsed.PS2_VeryStrong ? 'Y' : ''}
                        key="dropdown32"
                        placeholder="N"
                        options={dropDownOptions[32]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PS2_VeryStrong ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell><span style={fontStyleWritingMode}>Alleleic Data</span></Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="blue">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>BP2</Table.Cell>
                    <Table.Cell width={2}>Observed in trans with<br />dominant variant OR<br />observed in cis with<br />path variant</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.BP2 ? 'Y' : ''}
                        key="dropdown33"
                        placeholder="N"
                        options={dropDownOptions[33]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.BP2 ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
            <Table.Cell></Table.Cell>
            <Table.Cell>
              <Table size="small" color="orange">
                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell width={1}>PM3</Table.Cell>
                    <Table.Cell width={2}>Detected in trans with<br />P/LP variant<br />(recessive disorders)</Table.Cell>
                    <Table.Cell width={1}>
                      <Dropdown
                        value={criteriaUsed.PM3 ? 'Y' : ''}
                        key="dropdown34"
                        placeholder="N"
                        options={dropDownOptions[34]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM3 ? 'Y' : ''}
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
                        value={criteriaUsed.PM3_Strong ? 'Y' : ''}
                        key="dropdown35"
                        placeholder="N"
                        options={dropDownOptions[35]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM3_Strong ? 'Y' : ''}
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
                        value={criteriaUsed.PM3_VeryStrong ? 'Y' : ''}
                        key="dropdown36"
                        placeholder="N"
                        options={dropDownOptions[36]}
                        onChange={addOrRemoveCriteria}
                        text={criteriaUsed.PM3_VeryStrong ? 'Y' : ''}
                      />
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
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
