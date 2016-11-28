import React from 'react'
import { Breadcrumb } from 'semantic-ui-react'

const BreadCrumbs = ({ breadcrumbSections }) =>
  <div style={{ marginBottom: '10px' }}>
    {
      breadcrumbSections.map((label, i) => {
        return <Breadcrumb size="large" key={i}>{
          i < this.props.breadcrumbs.length - 1 ?
            (<Breadcrumb.Section><span style={{ marginRight: '10px' }}>
              {this.props.breadcrumbs[i]}</span> {'»'}
            </Breadcrumb.Section>) :
            (<Breadcrumb.Section active style={{ marginLeft: '10px' }}>
              {this.props.breadcrumbs[i]}
            </Breadcrumb.Section>)
        }
        </Breadcrumb>
      })
    }
  </div>


BreadCrumbs.propTypes = {
  breadcrumbSections: React.PropTypes.array.isRequired,
}

export default BreadCrumbs
