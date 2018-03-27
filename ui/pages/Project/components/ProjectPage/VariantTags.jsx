import React from 'react'
import PropTypes from 'prop-types'

import { Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { getProject } from 'redux/rootReducer'
import SectionHeader from 'shared/components/SectionHeader'


const VariantTags = props => (
  [
    <SectionHeader>Variant Tags</SectionHeader>,
    <div style={{ display: 'block', padding: '0px 0px 10px 0px' }}>
      {
        props.project.variantTagTypes && props.project.variantTagTypes.map(variantTagType => (
          <div key={variantTagType.variantTagTypeGuid} style={{ whitespace: 'nowrap' }}>
            {
              <span style={{ display: 'inline-block', minWidth: '35px', textAlign: 'right', fontSize: '11pt', paddingRight: '10px' }}>
                {variantTagType.numTags > 0 && <span style={{ fontWeight: 'bold' }}>{variantTagType.numTags}</span>}
              </span>
            }
            <Icon name="square" size="small" style={{ color: variantTagType.color }} />
            <a href={`/project/${props.project.deprecatedProjectId}/variants/${variantTagType.name}`}>{variantTagType.name}</a>
            {
              variantTagType.description &&
              <Popup
                position="right center"
                trigger={<Icon style={{ cursor: 'pointer', color: '#555555', marginLeft: '15px' }} name="help circle outline" />}
                content={variantTagType.description}
                size="small"
              />
            }
          </div>),
        )
      }
    </div>,
    <div style={{ paddingTop: '15px', paddingLeft: '35px' }}>
      <a href={`/project/${props.project.deprecatedProjectId}/saved-variants`}>View All</a>
    </div>,
  ]
)


VariantTags.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(VariantTags)
