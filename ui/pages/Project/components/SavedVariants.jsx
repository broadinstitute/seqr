import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Checkbox, Dropdown } from 'semantic-ui-react'

import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import Variants from 'shared/components/panel/variants/Variants'
import { VerticalSpacer, HorizontalSpacer } from 'shared/components/Spacers'
import { CLINSIG_SEVERITY } from 'shared/utils/constants'
import {
  getProject, getProjectSavedVariantsIsLoading, getProjectSavedVariants, loadProjectVariants,
} from '../reducers'

const clinsigSeverity = (clinvar) => {
  const significance = clinvar.clinsig && clinvar.clinsig.split('/')[0]
  if (!significance) return -10
  return significance in CLINSIG_SEVERITY ? CLINSIG_SEVERITY[significance] : -0.5
}

const sortOptions = [
  { key: 'familyGuid', value: 'familyGuid', text: 'Family' },
  { key: 'position', value: 'xpos', text: 'Position' },
  { key: 'clinvar', value: 'clinvar', text: 'Clinvar Significance' },
  { key: 'inDiseaseGeneDb', value: 'genes', text: 'In OMIM' },
]

const sortFuncs = {
  familyGuid: (a, b) => a.localeCompare(b),
  xpos: (a, b) => a - b,
  clinvar: (a, b) => clinsigSeverity(b) - clinsigSeverity(a),
  genes: (a, b) => b.some(gene => gene.inDiseaseDb) - a.some(gene => gene.inDiseaseDb),
}

class SavedVariants extends React.Component {

  static propTypes = {
    match: PropTypes.object,
    project: PropTypes.object,
    loading: PropTypes.bool,
    savedVariants: PropTypes.array,
    loadProjectVariants: PropTypes.func,
  }

  constructor(props) {
    super(props)

    props.loadProjectVariants(props.match.params.tag)
    this.state = {
      hideExcluded: false,
      category: 'All',
      sort: props.match.params.familyGuid ? 'xpos' : 'familyGuid',
    }
  }

  render() {
    const { familyGuid, tag } = this.props.match.params
    let variantsToShow = (this.props.savedVariants || [])
    if (familyGuid) {
      // TODO only fetch variants for family in the first place
      variantsToShow = variantsToShow.filter(variant => variant.familyGuid === familyGuid)
    }
    const variantCount = variantsToShow.length
    if (this.state.hideExcluded) {
      variantsToShow = variantsToShow.filter(variant => variant.tags.every(t => t.name !== 'Excluded'))
    }
    if (this.state.category !== 'All' && !tag) {
      variantsToShow = variantsToShow.filter(variant => variant.tags.some(t => t.category === this.state.category))
    }
    // Always secondary sort on xpos
    variantsToShow.sort((a, b) => {
      return sortFuncs[this.state.sort](a[this.state.sort], b[this.state.sort]) || a.xpos - b.xpos
    })

    const categoryOptions = [...new Set(
      this.props.project.variantTagTypes.map(type => type.category).filter(category => category),
    )].map((category) => { return { value: category, text: category, key: category } })

    return (
      <div>
        <div style={{ paddingTop: '20px', paddingBottom: '20px' }}>
          <HorizontalStackedBar
            height={30}
            minPercent={0.1}
            title="Saved Variants"
            linkPath={`/project/${this.props.project.projectGuid}/saved_variants${familyGuid ? `/family/${familyGuid}` : ''}`}
            data={this.props.project.variantTagTypes.map((vtt) => {
              return { count: familyGuid ? vtt.tagCounts[familyGuid] || 0 : vtt.numTags, ...vtt }
            })}
          />
          <VerticalSpacer height={10} />
          {!this.props.loading &&
            <span>
              Showing {variantsToShow.length} of {variantCount} {tag && <b>{`"${tag}"`}</b>} variants
            </span>
          }
          <div style={{ float: 'right' }}>
            Sort by:
            <HorizontalSpacer width={5} />
            <Dropdown
              inline
              onChange={(e, data) => this.setState({ sort: data.value })}
              value={this.state.sort}
              options={familyGuid ? sortOptions.slice(1) : sortOptions}
            />
            <HorizontalSpacer width={20} />
            {
              !tag && categoryOptions.length > 0 &&
              <span>
                Show category:
                <HorizontalSpacer width={5} />
                <Dropdown
                  inline
                  onChange={(e, data) => this.setState({ category: data.value })}
                  value={this.state.category}
                  options={[{ value: 'All', text: 'All', key: 'all' }, ...categoryOptions]}
                />
                <HorizontalSpacer width={15} />
              </span>
            }
            <Checkbox toggle label="Hide Excluded" onChange={(e, data) => this.setState({ hideExcluded: data.checked })} />
          </div>
          <VerticalSpacer height={20} />
        </div>
        {this.props.loading ?
          <Loader inline="centered" active /> :
          <div style={{ paddingTop: '20px' }}><Variants variants={variantsToShow} /></div>
        }
      </div>
    )
  }
}

const mapStateToProps = (state, ownProps) => ({
  project: getProject(state),
  loading: getProjectSavedVariantsIsLoading(state),
  savedVariants: getProjectSavedVariants(state, ownProps.match.params.tag),
})

const mapDispatchToProps = {
  loadProjectVariants,
}

export default connect(mapStateToProps, mapDispatchToProps)(SavedVariants)

