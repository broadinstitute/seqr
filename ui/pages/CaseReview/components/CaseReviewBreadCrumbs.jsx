import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import styled from 'styled-components'
import BreadCrumbs from 'shared/components/page/BreadCrumbs'
import { computeDashboardUrl, computeProjectUrl } from 'shared/utils/urlUtils'


const Container = styled.div`
  margin-top: 35px;
`

const CaseReviewBreadCrumbs = (props) => {
  document.title = `Case Review: ${props.project.name}`

  return (
    <Container>
      <BreadCrumbs
        breadcrumbSections={[
          <a href={computeDashboardUrl()}>Home</a>,
          <a href={computeProjectUrl(props.project.projectGuid)}>{props.project.name}</a>,
          'Case Review',
        ]}
      />
    </Container>)
}

export { CaseReviewBreadCrumbs as CaseReviewBreadCrumbsComponent }

CaseReviewBreadCrumbs.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = ({ project }) => ({ project })

export default connect(mapStateToProps)(CaseReviewBreadCrumbs)
