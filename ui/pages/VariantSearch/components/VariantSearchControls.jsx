/* eslint-disable */

import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import styled from 'styled-components'
import { Checkbox, Grid, Dropdown } from 'semantic-ui-react'
import { getProject, getFamily, getFamiliesByGuid } from 'redux/utils/commonDataActionsAndSelectors'


const Container = styled.div`
   margin: 0px 100px; 
`

const Heading = styled.div`
  border-bottom: 1px solid #EEE;
  line-height: 30px;
  font-size: 20px;
  font-weight: 300;
  padding-top: 8px;
  padding-bottom: 6px;
  margin: 8px 0 15px 0;
`

const StyledButton = styled.a`
  text-decoration: none;
  background-color: white;
  border-radius: 5px;
  display: block;
  padding: 10px 15px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1.5;
`
const RegularButton = StyledButton.extend`
  :hover {
    background-color: #eee;
    color: #2a6496;
  }
`

const SelectedButton = StyledButton.extend`
  color: #fff;
  :hover {
    color: #fff;
  }
  text-decoration: none;
  background-color: #428bca;
  border-radius: 5px;
  display: block;
  padding: 10px 15px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1.5;
`

const SectionContainer = styled.div`
  margin-left: 10px;
  padding-bottom: 15px;
`

const SectionLabel = styled.div`
  font-weight: bold;
  font-style: italic;
  display: inline;
`

const IndentedDiv = styled.div`
  margin-left: 30px;
`

const CheckboxContainer = styled.div`
  margin: 7px 0px;
`


class VariantSearchControls extends React.Component
{
  static propTypes = {
    project: PropTypes.object.isRequired,
    family: PropTypes.object,
    families: PropTypes.object,
  }

  constructor() {
    super()

    this.formDataJson = {}
  }

  render() {

    return (
      <Container>
        <Grid>
          <Grid.Row>
            <Grid.Column width={16}>
              <Heading>Search Method</Heading>
            </Grid.Column>
          </Grid.Row>
          <Grid.Row>
            <Grid.Column width={4}>
              <SelectedButton role="button">Mendelian Inheritance</SelectedButton>
              <RegularButton role="button">Custom Inheritance</RegularButton>
              <RegularButton role="button">All Variants</RegularButton>
            </Grid.Column>
            <Grid.Column width={12}>
              <SectionLabel>Families:</SectionLabel> Variants will be returned if they pass the inheritance
              mode filter in at least one of these families.
              <SectionContainer>
                <div style={{ maxWidth: '350px', margin: '10px 10px 10px 7px' }}>
                  <Dropdown placeholder="Select families" fluid multiple search selection options={
                    Object.entries(this.props.families).map(([familyGuid, family]) => (
                      { key: familyGuid, text: family.familyId, value: familyGuid }
                    ))
                  }
                  />
                </div>
              </SectionContainer>
              <SectionLabel>Datasets:</SectionLabel> Select datasets to include in the search.
              <SectionContainer>
                <CheckboxContainer><Checkbox label={<label>WGS callset - 37 samples loaded on 2017-11-13</label>} /></CheckboxContainer>
                <CheckboxContainer><Checkbox label={<label>Manta SV callset - 5 samples loaded on 2017-11-13</label>} /></CheckboxContainer>
              </SectionContainer>
              <SectionLabel>Inheritance Mode:</SectionLabel> Variants will be returned that segregate with the selected inheritance model(s).
              <SectionContainer>
                <CheckboxContainer><Checkbox label={<label>Recessive</label>} /></CheckboxContainer>
                <IndentedDiv>
                  <CheckboxContainer><Checkbox label={<label>Homozygous Recessive</label>} /></CheckboxContainer>
                  <CheckboxContainer><Checkbox label={<label>Compound Heterozygous</label>} /></CheckboxContainer>
                </IndentedDiv>
                <CheckboxContainer><Checkbox label={<label>X-Linked</label>} /></CheckboxContainer>
                <CheckboxContainer><Checkbox label={<label>Dominant</label>} /></CheckboxContainer>
                <CheckboxContainer><Checkbox label={<label>De-novo</label>} /></CheckboxContainer>
              </SectionContainer>
            </Grid.Column>
          </Grid.Row>
          <Grid.Row style={{ height: '200px' }}>.</Grid.Row>
        </Grid>
      </Container>)
  }
}


export { VariantSearchControls as VariantSearchControlsComponent }

VariantSearchControls.propTypes = {
  //user: PropTypes.object.isRequired,
  //project: PropTypes.object.isRequired,
  //family: PropTypes.object,
}

const mapStateToProps = state => ({
  //user: getUser(state),
  project: getProject(state),
  family: getFamily(state),
  families: getFamiliesByGuid(state),
})

export default connect(mapStateToProps)(VariantSearchControls)
