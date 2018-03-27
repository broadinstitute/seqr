import React from 'react'
import PropTypes from 'prop-types'
import { Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'

import ShowIfEditPermissions from 'shared/components/ShowIfEditPermissions'
import { getProject } from 'redux/rootReducer'
import SectionHeader from 'shared/components/SectionHeader'


const GeneLists = props => (
  [
    <SectionHeader key="header">Gene Lists</SectionHeader>,
    <div key="content" style={{ marginBottom: '14px' }}>
      {
        props.project.locusLists &&
        props.project.locusLists.map(locusList => (
          <div key={locusList.locusListGuid} style={{ padding: '2px 0px', whitespace: 'nowrap' }}>
            {locusList.name}
            <span style={{ paddingLeft: '10px' }}>
              <i>
                <a href={`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`}>
                  {`${locusList.numEntries} entries`}
                </a>
              </i>
            </span>
            {
              locusList.description &&
              <Popup
                position="right center"
                trigger={<Icon style={{ cursor: 'pointer', color: '#555555', marginLeft: '10px' }} name="help circle outline" />}
                content={locusList.description}
                size="small"
              />
            }
          </div>),
        )
      }
    </div>,
    <ShowIfEditPermissions key="edit">
      <a href={`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`}>
        Edit Gene Lists
      </a>
    </ShowIfEditPermissions>,
  ]
)


GeneLists.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(GeneLists)
