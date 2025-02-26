import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Divider, Button, Header } from 'semantic-ui-react'

import { navigateFamiliesSearch } from 'redux/rootReducer'
import { NoHoverFamilyLink } from 'shared/components/buttons/FamilyLink'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import { Phenotypes } from 'shared/components/panel/MatchmakerPanel'
import DataTable from 'shared/components/table/DataTable'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { ButtonLink } from 'shared/components/StyledComponents'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { GENOME_VERSION_LOOKUP } from 'shared/utils/constants'

const SEARCH_CATEGORIES = ['hpo_terms']
const ID_FIELD = 'individualGuid'
const COLUMNS = [
  {
    name: 'familyId',
    content: 'Family',
    format: row => <b><NoHoverFamilyLink family={row.familyData} target="_blank" /></b>,
  },
  { name: 'displayName', content: 'Individual' },
  {
    name: 'features',
    content: 'HPO Terms',
    format: row => <Phenotypes phenotypes={row.features} highlightIds={row.matchedTerms} maxWidth="800px" />,
  },
]

class Hpo extends React.PureComponent {

  static propTypes = {
    navigateSearch: PropTypes.func.isRequired,
  }

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
        this.setState((prevState) => {
          const prevDataById = prevState.data.reduce((acc, row) => ({ ...acc, [row[ID_FIELD]]: row }), {})
          const dataById = responseJson.data.reduce((acc, row) => {
            if (!acc[row[ID_FIELD]]) {
              acc[row[ID_FIELD]] = { ...row, matchedTerms: [] }
            }
            acc[row[ID_FIELD]].matchedTerms.push(result.key)
            return acc
          }, prevDataById)
          return { loading: false, data: Object.values(dataById) }
        })
      },
      (e) => {
        this.setState({ loading: false, error: e.message })
      }).get()
  }

  removeTerm = (e, { term }) => {
    this.setState(prevState => ({
      terms: prevState.terms.filter(({ key }) => key !== term),
      data: prevState.data.map(
        ({ matchedTerms, ...row }) => ({ ...row, matchedTerms: matchedTerms.filter(m => m !== term) }),
      ).filter(({ matchedTerms }) => matchedTerms.length),
    }))
  }

  render() {
    const { terms, data, loading, error } = this.state
    const { navigateSearch } = this.props

    const familiesByGenomeVersion = data.reduce((acc, { familyData }) => {
      if (!acc[familyData.genomeVersion]) {
        acc[familyData.genomeVersion] = {}
      }
      acc[familyData.genomeVersion][familyData.familyGuid] = familyData.projectGuid
      return acc
    }, {})

    const numFamilies = Object.values(familiesByGenomeVersion).reduce(
      (acc, families) => acc + Object.keys(families).length, 0,
    )

    const genomeProjectFamilies = Object.entries(familiesByGenomeVersion).map(([genomeVersion, familyAcc]) => {
      const families = Object.entries(familyAcc)
      const projectFamilies = families.reduce(
        (acc, [familyGuid, projectGuid]) => {
          if (!acc[projectGuid]) {
            acc[projectGuid] = []
          }
          acc[projectGuid].push(familyGuid)
          return acc
        }, {},
      )
      return [genomeVersion, projectFamilies]
    })

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
          <Header size="medium">
            <Header.Content>{`${numFamilies} Families, ${data.length} Individuals`}</Header.Content>
            <Header.Subheader>
              {genomeProjectFamilies.map(([genomeVersion, projectFamilies]) => (
                <span key={genomeVersion}>
                  {`${GENOME_VERSION_LOOKUP[genomeVersion]}: `}
                  <ButtonLink
                    onClick={navigateSearch}
                    projectFamilies={projectFamilies}
                  >
                    {`Variant Search - ${Object.keys(familiesByGenomeVersion[genomeVersion]).length} Families`}
                  </ButtonLink>
                </span>
              ))}
            </Header.Subheader>
          </Header>
        )}
        <DataTable
          data={data}
          loading={loading}
          idField={ID_FIELD}
          defaultSortColumn="familyId"
          emptyContent={error || (terms.length ? 'No families with selected terms' : 'Select an HPO term')}
          columns={COLUMNS}
          collapsing
        />
      </div>
    )
  }

}

const mapDispatchToProps = dispatch => ({
  navigateSearch: (e, { projectFamilies }) => {
    e.stopPropagation()
    dispatch(navigateFamiliesSearch(projectFamilies))
  },
})

export default connect(null, mapDispatchToProps)(Hpo)
