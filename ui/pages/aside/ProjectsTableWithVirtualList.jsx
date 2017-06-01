import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
//import { Button, Grid, Table } from 'semantic-ui-react'
import { AutoSizer, List, WindowScroller } from 'react-virtualized'

import ProjectTableHeader from './ProjectTableHeader'
import ProjectTableRow from './ProjectTableRow'

class ProjectsTable extends React.Component {

  static propTypes = {
    //user: PropTypes.object.isRequired,
    projectsByGuid: PropTypes.object.isRequired,
  }

  constructor(props) {
    super(props)

    this.projectGuids = Object.keys(props.projectsByGuid)
  }

  componentWillReceiveProps(nextProps) {
    this.projectGuids = Object.keys(nextProps.projectsByGuid)

    this.getRowHeight.bind(this)
  }

  renderRow({ index, key, style }) {
    const projectGuid = this.projectGuids[index]
    return <div key={key} style={style}>
      <ProjectTableRow index={index} style={style} projectGuid={projectGuid} projectsByGuid={this.props.projectsByGuid} />
    </div>
  }

  render() {
    return <div style={{ width: '100%' }}>
      <WindowScroller>
        {({ height, scrollTop }) => (
          <AutoSizer disableHeight>
            {({ width }) => <div style={{ width }}>
              <ProjectTableHeader projectsByGuid={this.props.projectsByGuid} />
              <List
                autoHeight
                height={height}
                overscanRowCount={20}
                rowCount={this.projectGuids.length}
                rowHeight={this.getRowHeight}
                rowRenderer={({ index, key, style }) => this.renderRow({ index, key, style })}
                scrollTop={scrollTop}
                width={width}
              />
            </div>
            }
          </AutoSizer>
        )}
      </WindowScroller>
    </div>
  }

  getRowHeight({ index }) {
    console.log('getRowHeight PROJECT GUIDs', this.props)
    return this.projectGuids[index % this.projectGuids.length].size
  }

}

const mapStateToProps = ({ user, projectsByGuid }) => ({ user, projectsByGuid })

export default connect(mapStateToProps)(ProjectsTable)
