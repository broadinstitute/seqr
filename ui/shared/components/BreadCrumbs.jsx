import React from 'react'
import { Breadcrumb } from 'semantic-ui-react'

const BreadCrumbs = props =>
  <div style={{ marginBottom: '10px' }}>
    {
      props.breadcrumbSections.map((label, i) => {
        return <Breadcrumb size="large" key={i}>{
          i < props.breadcrumbSections.length - 1 ?
            (<Breadcrumb.Section>
              <span style={{ marginRight: '10px' }}>
                {props.breadcrumbSections[i]}
              </span> {'»'}
            </Breadcrumb.Section>) :
            (<Breadcrumb.Section active style={{ marginLeft: '10px' }}>
              {props.breadcrumbSections[i]}
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
