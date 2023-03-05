import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Popup, Icon } from 'semantic-ui-react'

import { loadFamilyDetails } from 'redux/rootReducer'
import {
  getFamiliesByGuid,
  getFamilyDetailsLoading,
  getSortedIndividualsByFamily,
  getGenesById,
  getHasActiveSearchableSampleByFamily,
} from 'redux/selectors'
import { FAMILY_DETAIL_FIELDS, getVariantMainGeneId } from 'shared/utils/constants'
import Family from 'shared/components/panel/family/Family'
import FamilyReads from 'shared/components/panel/family/FamilyReads'
import DataLoader from 'shared/components/DataLoader'
import { VerticalSpacer, HorizontalSpacer } from 'shared/components/Spacers'
import { HelpIcon, ButtonLink } from 'shared/components/StyledComponents'

import { loadFamilyVariantSummary } from '../reducers'
import {
  getCurrentProject, getFamilyVariantSummaryLoading, getFamilyTagTypeCounts,
} from '../selectors'
import IndividualRow from './FamilyTable/IndividualRow'
import CreateVariantButton from './CreateVariantButton'
import VariantTagTypeBar from './VariantTagTypeBar'

const READ_BUTTON_PROPS = { padding: '0.5em 0 1.5em 0' }

const SearchLink = React.memo(({ family, disabled, children }) => (
  <ButtonLink as={Link} to={`/variant_search/family/${family.familyGuid}`} disabled={disabled}>{children}</ButtonLink>
))

SearchLink.propTypes = {
  family: PropTypes.object.isRequired,
  disabled: PropTypes.bool,
  children: PropTypes.node,
}

const DiscoveryGenes = React.memo(({ family, genesById }) => {
  const discoveryGenes = (family.discoveryTags || []).map(
    tag => (genesById[getVariantMainGeneId(tag)] || {}).geneSymbol,
  ).filter(val => val)
  return discoveryGenes.length > 0 ? (
    <span>
      <b>Discovery Genes: </b>
      {[...new Set(discoveryGenes)].join(', ')}
    </span>
  ) : null
})

DiscoveryGenes.propTypes = {
  family: PropTypes.object.isRequired,
  genesById: PropTypes.object.isRequired,
}

const BaseVariantDetail = (
  { project, family, hasActiveVariantSample, compact, genesById, tagTypeCounts, load, loading },
) => (
  <DataLoader load={load} contentId={family.familyGuid} content={family.discoveryTags} loading={loading}>
    <VariantTagTypeBar
      height={15}
      width="calc(100% - 2.5em)"
      projectGuid={project.projectGuid}
      familyGuid={family.familyGuid}
      tagTypeCounts={tagTypeCounts}
      tagTypes={project.variantTagTypes}
      sectionLinks={false}
    />
    <HorizontalSpacer width={10} />
    <SearchLink family={family} disabled={!hasActiveVariantSample}><Icon name="search" /></SearchLink>
    <DiscoveryGenes family={family} genesById={genesById} />
    {!compact && (
      <div>
        <VerticalSpacer height={20} />
        <SearchLink family={family} disabled={!hasActiveVariantSample}>
          <Icon name="search" />
          &nbsp; Variant Search
        </SearchLink>
        {!hasActiveVariantSample && (
          <Popup
            trigger={<HelpIcon />}
            content={`Search is disabled until data is loaded${project.workspaceName ? '. Loading data from AnVIL to seqr is a slow process, and generally takes a week.' : ''}`}
          />
        )}
        <VerticalSpacer height={10} />
        <CreateVariantButton family={family} />
        <VerticalSpacer height={10} />
        {project.isMmeEnabled && (
          <Link to={`/project/${project.projectGuid}/family_page/${family.familyGuid}/matchmaker_exchange`}>
            MatchMaker Exchange
          </Link>
        )}
      </div>
    )}
  </DataLoader>
)

BaseVariantDetail.propTypes = {
  family: PropTypes.object,
  project: PropTypes.object,
  genesById: PropTypes.object,
  compact: PropTypes.bool,
  hasActiveVariantSample: PropTypes.bool,
  tagTypeCounts: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapVariantDetailStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  genesById: getGenesById(state),
  hasActiveVariantSample: (getHasActiveSearchableSampleByFamily(state)[ownProps.family.familyGuid] || {}).isSearchable,
  loading: getFamilyVariantSummaryLoading(state),
  tagTypeCounts: getFamilyTagTypeCounts(state)[ownProps.family.familyGuid] || {},
})

const mapVariantDetailDispatchToProps = {
  load: loadFamilyVariantSummary,
}

const VariantDetail = connect(mapVariantDetailStateToProps, mapVariantDetailDispatchToProps)(BaseVariantDetail)

const FamilyReadsLayout = ({ reads, showReads }) => (
  <div>
    {showReads}
    {reads}
  </div>
)

FamilyReadsLayout.propTypes = {
  reads: PropTypes.object,
  showReads: PropTypes.object,
}

const BaseExpandedFamily = React.memo(({ familyDetail, familyGuid, family, individuals, tableName, loading, load }) => (
  <DataLoader load={load} contentId={familyGuid} content={family && family.detailsLoaded} loading={loading}>
    {familyDetail}
    <FamilyReads layout={FamilyReadsLayout} familyGuid={familyGuid} buttonProps={READ_BUTTON_PROPS} />
    {individuals && individuals.map(individual => (
      <IndividualRow
        key={individual.individualGuid}
        individual={individual}
        tableName={tableName}
      />
    ))}
  </DataLoader>
))

BaseExpandedFamily.propTypes = {
  familyGuid: PropTypes.string.isRequired,
  familyDetail: PropTypes.node,
  family: PropTypes.object,
  individuals: PropTypes.arrayOf(PropTypes.object),
  tableName: PropTypes.string,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapExpandedStateToProps = (state, ownProps) => ({
  loading: !!getFamilyDetailsLoading(state)[ownProps.familyGuid],
  individuals: getSortedIndividualsByFamily(state)[ownProps.familyGuid],
})

const mapDispatchToProps = {
  load: loadFamilyDetails,
}

const ExpandedFamily = connect(mapExpandedStateToProps, mapDispatchToProps)(BaseExpandedFamily)

const BaseFamilyDetail = React.memo(({ familyGuid, family, compact, tableName, showVariantDetails, ...props }) => {
  const familyDetail = (
    <Family
      family={family}
      compact={compact}
      rightContent={showVariantDetails ? <VariantDetail family={family} compact={compact} /> : <div />}
      {...props}
    />
  )
  if (compact) {
    return familyDetail
  }
  return <ExpandedFamily familyGuid={familyGuid} family={family} familyDetail={familyDetail} tableName={tableName} />
})

BaseFamilyDetail.propTypes = {
  familyGuid: PropTypes.string.isRequired,
  family: PropTypes.object,
  individuals: PropTypes.arrayOf(PropTypes.object),
  compact: PropTypes.bool,
  showVariantDetails: PropTypes.bool,
  tableName: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => ({
  family: getFamiliesByGuid(state)[ownProps.familyGuid],
  project: getCurrentProject(state),
})

export const FamilyDetail = connect(mapStateToProps)(BaseFamilyDetail)

const FamilyPage = ({ match }) => (
  <FamilyDetail
    familyGuid={match.params.familyGuid}
    showVariantDetails
    fields={FAMILY_DETAIL_FIELDS}
  />
)

FamilyPage.propTypes = {
  match: PropTypes.object,
}

export default FamilyPage
