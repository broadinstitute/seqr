import React from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { getProject } from 'redux/rootReducer'


const VariantTags = props => (
  <div key="content" style={{ display: 'block', padding: '0px 0px 10px 0px' }}>
    {
      props.project.variantTagTypes && props.project.variantTagTypes.map(variantTagType => (
        <div key={variantTagType.variantTagTypeGuid} style={{ whitespace: 'nowrap' }}>
          {
            <span style={{ display: 'inline-block', minWidth: '35px', textAlign: 'right', fontSize: '11pt', paddingRight: '10px' }}>
              {variantTagType.numTags > 0 && <span style={{ fontWeight: 'bold' }}>{variantTagType.numTags}</span>}
            </span>
          }
          <Icon name="square" size="small" style={{ color: variantTagType.color }} />
          <Link to={`/project/${props.project.projectGuid}/saved_variants/${variantTagType.name}`}>{variantTagType.name}</Link>
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
  </div>
)


VariantTags.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(VariantTags)
