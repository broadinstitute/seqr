import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Popup, Icon } from 'semantic-ui-react'

import {
  getFamiliesByGuid,
  getSortedIndividualsByFamily,
  getGenesById,
  getHasActiveVariantSampleByFamily,
} from 'redux/selectors'
import { FAMILY_DETAIL_FIELDS, getVariantMainGeneId } from 'shared/utils/constants'
import Family from 'shared/components/panel/family/Family'
import FamilyReads from 'shared/components/panel/family/FamilyReads'
import { VerticalSpacer, HorizontalSpacer } from 'shared/components/Spacers'
import { HelpIcon, ButtonLink } from 'shared/components/StyledComponents'

import { getCurrentProject } from '../selectors'
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

const DiscoveryGenes = React.memo(({ project, familyGuid, genesById }) => {
  const discoveryGenes = project.discoveryTags.filter(tag => tag.familyGuids.includes(familyGuid)).map(tag =>
    (genesById[getVariantMainGeneId(tag)] || {}).geneSymbol).filter(val => val)
  return discoveryGenes.length > 0 ? (
    <span> <b>Discovery Genes:</b> {[...new Set(discoveryGenes)].join(', ')}</span>
  ) : null
})

DiscoveryGenes.propTypes = {
  project: PropTypes.object.isRequired,
  familyGuid: PropTypes.string.isRequired,
  genesById: PropTypes.object.isRequired,
}

const BaseVariantDetail = ({ project, family, hasActiveVariantSample, compact, genesById }) =>
  <div>
    <VariantTagTypeBar height={15} width="calc(100% - 2.5em)" project={project} familyGuid={family.familyGuid} sectionLinks={false} />
    <HorizontalSpacer width={10} />
    <SearchLink family={family} disabled={!hasActiveVariantSample}><Icon name="search" /></SearchLink>
    <DiscoveryGenes project={project} familyGuid={family.familyGuid} genesById={genesById} />
    {!compact &&
      <div>
        <VerticalSpacer height={20} />
        <SearchLink family={family} disabled={!hasActiveVariantSample}><Icon name="search" /> Variant Search</SearchLink>
        {!hasActiveVariantSample &&
          <Popup
            trigger={<HelpIcon />}
            content={`Search is disabled until data is loaded${project.workspaceName ? '. Loading data from AnVIL to seqr is a slow process, and generally takes a week.' : ''}`}
          />}
        <VerticalSpacer height={10} />
        <CreateVariantButton family={family} />
        <VerticalSpacer height={10} />
        {project.isMmeEnabled &&
          <Link to={`/project/${project.projectGuid}/family_page/${family.familyGuid}/matchmaker_exchange`}>
            MatchMaker Exchange
          </Link>
        }
      </div>
    }
  </div>

BaseVariantDetail.propTypes = {
  family: PropTypes.object,
  project: PropTypes.object,
  genesById: PropTypes.object,
  compact: PropTypes.bool,
  hasActiveVariantSample: PropTypes.bool,
}

const mapVariantDetailStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  genesById: getGenesById(state),
  hasActiveVariantSample: getHasActiveVariantSampleByFamily(state)[ownProps.family.familyGuid],
})

const VariantDetail = connect(mapVariantDetailStateToProps)(BaseVariantDetail)

const BaseFamilyDetail = React.memo(({ family, individuals, compact, tableName, showVariantDetails, ...props }) =>
  <div>
    <Family
      family={family}
      compact={compact}
      rightContent={showVariantDetails ? <VariantDetail family={family} compact={compact} /> : null}
      {...props}
    />
    {!compact && <FamilyReads
      layout={({ reads, showReads }) =>
        <div>
          {showReads}
          {reads}
        </div>}
      familyGuid={family.familyGuid}
      buttonProps={READ_BUTTON_PROPS}
    />}
    {individuals && individuals.map(individual => (
      <IndividualRow
        key={individual.individualGuid}
        individual={individual}
        tableName={tableName}
      />),
    )}
  </div>,
)

BaseFamilyDetail.propTypes = {
  family: PropTypes.object.isRequired,
  individuals: PropTypes.array,
  compact: PropTypes.bool,
  showVariantDetails: PropTypes.bool,
  tableName: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => ({
  family: getFamiliesByGuid(state)[ownProps.familyGuid],
  project: getCurrentProject(state),
  individuals: ownProps.showIndividuals ? getSortedIndividualsByFamily(state)[ownProps.familyGuid] : null,
})

export const FamilyDetail = connect(mapStateToProps)(BaseFamilyDetail)

const FamilyPage = ({ match }) =>
  <FamilyDetail
    familyGuid={match.params.familyGuid}
    showVariantDetails
    showDetails
    showIndividuals
    fields={FAMILY_DETAIL_FIELDS}
  />

FamilyPage.propTypes = {
  match: PropTypes.object,
}

export default FamilyPage
