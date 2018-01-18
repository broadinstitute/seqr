import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import styled from 'styled-components'
import { getProject, getFamily } from 'shared/utils/redux/commonDataActionsAndSelectors'
import { computeProjectUrl } from 'shared/utils/urlUtils'

const Heading = styled.div`
   font-size: 36px;
   font-weight: 300;
   line-height: 1em;
   padding-bottom: 10px;
`

const SubHeading = styled.div`
   font-size: 16px;
   line-height: 1.5em;
   padding-bottom: 5px;
`

const Container = styled.div`
   margin: 40px 0px 0px 110px; 
`

const VariantPageHeader = props =>
  <Container>
    <Heading>Variant Search</Heading>
    <SubHeading>
      Family: <a href={`/project/${props.project.deprecatedProjectId}/family/${props.family.familyId}`}>{props.family.familyId}</a><br />
      Project: <a href={computeProjectUrl(props.project.projectGuid)}>{props.project.name}</a><br />
    </SubHeading>
  </Container>


export { VariantPageHeader as VariantPageHeaderComponent }

VariantPageHeader.propTypes = {
  //user: PropTypes.object.isRequired,
  project: PropTypes.object.isRequired,
  family: PropTypes.object,
}

const mapStateToProps = state => ({
  //user: getUser(state),
  project: getProject(state),
  family: getFamily(state),
})

export default connect(mapStateToProps)(VariantPageHeader)
