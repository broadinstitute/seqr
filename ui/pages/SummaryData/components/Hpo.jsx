import React from 'react'
import { Divider, Button, Header } from 'semantic-ui-react'

import { NoHoverFamilyLink } from 'shared/components/buttons/FamilyLink'
import SearchResultsLink from 'shared/components/buttons/SearchResultsLink'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import { Phenotypes } from 'shared/components/panel/MatchmakerPanel'
import DataTable from 'shared/components/table/DataTable'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

const SEARCH_CATEGORIES = ['hpo_terms']

const COLUMNS = [
  {
    name: 'familyId',
    content: 'Family',
    format: row => <b><NoHoverFamilyLink family={row.familyData} /></b>,
  },
  { name: 'displayName', content: 'Individual' },
  {
    name: 'features',
    content: 'HPO Terms',
    format: row => <Phenotypes phenotypes={row.features} maxWidth="600px" />,
  },
]

class Hpo extends React.PureComponent {

  static propTypes = {}

  state = {
    data: [],
    terms: [],
    loading: false,
    error: null,
  }

  loadTermData = (result) => {
    this.setState(prevState => ({ loading: true, terms: prevState.terms.concat(result) }))
    new HttpRequestHelper(`/api/summary_data/hpo/${result.key}`,
      (responseJson) => {
        // TODO merge with previous data
        this.setState({ loading: false, data: responseJson.data })
      },
      (e) => {
        this.setState({ loading: false, error: e.message })
      }).get()
  }

  removeTerm = (e, { term }) => {
    // TODO filter removed data
    this.setState(prevState => ({ terms: prevState.terms.filter(({ key }) => key !== term) }))
  }

  render() {
    const { terms, data, loading, error } = this.state
    const familyGuids = new Set(data.map(({ familyData }) => familyData.familyGuid))
    return (
      <div>
        <AwesomeBar
          categories={SEARCH_CATEGORIES}
          inputwidth="300px"
          placeholder="Search for an HPO term"
          onResultSelect={this.loadTermData}
        />
        <HorizontalSpacer width={10} />
        {terms.map(({ title, description, key }) => (
          <Button
            key={key}
            term={key}
            content={`${title} ${description}`}
            onClick={this.removeTerm}
            size="tiny"
            color="grey"
            icon="delete"
            compact
          />
        ))}
        <Divider />
        {terms.length > 0 && (
          <Header size="small">
            <Header.Content>{`${familyGuids.size} Families, ${data.length} Individuals: `}</Header.Content>
            <HorizontalSpacer width={10} />
            {/* TODO search link does not work */}
            <SearchResultsLink disabled={data.length === 0} buttonText="Variant Search" />
          </Header>
        )}
        <DataTable
          data={data}
          loading={loading}
          idField="individualGuid"
          defaultSortColumn="familyId"
          emptyContent={error || (terms.length ? 'No families with selected terms' : 'Select an HPO term')}
          columns={COLUMNS}
          collapsing
        />
      </div>
    )
  }

}

export default Hpo
