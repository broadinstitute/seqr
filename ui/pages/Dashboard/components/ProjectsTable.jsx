/* eslint no-undef: "warn" */
import React from 'react'
//import { Button, Grid, Table } from 'semantic-ui-react'
import { AutoSizer, List, WindowScroller } from 'react-virtualized'

import CaseReviewLink from './CaseReviewLink'


class ProjectsTable extends React.Component {

  static propTypes = {
    user: React.PropTypes.object.isRequired,
    projectsByGuid: React.PropTypes.object.isRequired,
  }

  constructor(props) {
    super(props)
    console.log('constructor')
    this.projectGuids = Object.keys(props.projectsByGuid)
  }

  componentWillReceiveProps(nextProps) {
    console.log('component will update')
    this.projectGuids = Object.keys(nextProps.projectsByGuid)
  }

  rowRenderer({ index, key, style }) {
    const projectGuid = this.projectGuids[index]
    const user = this.props.user
    return (
      <div key={key} style={style}>
        {projectGuid} &nbsp; &nbsp;
        {
          user.is_staff &&
          <CaseReviewLink projectGuid={projectGuid} />
        }
      </div>
    )
  }

  render() {
    console.log('rendering', this.projectGuids.length)
    return <div style={{ width: '100%' }}>
      <WindowScroller>
        {({ height, scrollTop }) => (
          <AutoSizer disableHeight>
            {({ width }) => {
              return <List
                autoHeight
                height={height}
                overscanRowCount={5}
                rowCount={this.projectGuids.length}
                rowHeight={30}
                rowRenderer={({ index, key, style }) => this.rowRenderer({ index, key, style })}
                scrollTop={scrollTop}
                width={width}
              />
            }}
          </AutoSizer>
        )}
      </WindowScroller>
    </div>
  }
}

export default ProjectsTable
