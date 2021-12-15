import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Icon, List } from 'semantic-ui-react'
import styled from 'styled-components'

import { getGenesById } from 'redux/selectors'
import { GENOME_VERSION_DISPLAY_LOOKUP } from 'shared/utils/constants'
import ShowGeneModal from '../buttons/ShowGeneModal'

const PhenotypeListItem = styled(({ maxWidth, observed, ...props }) => <List.Item {...props} />)`
  text-decoration: ${props => (props.observed === 'no' ? 'line-through' : 'none')};
  max-width: ${props => props.maxWidth || 'inherit'};
`

const SequenceContainer = styled.div`
  max-width: 100px;
  display: inline-block;
  text-overflow: ellipsis;
  overflow-x: hidden;
  vertical-align: bottom;
  padding-left: 5px;
  padding-right: 5px;
`

const TopAlignedItem = styled(List.Item)`
  vertical-align: top;
`

const NoEmphasis = styled.span`
  color: grey;
`

const variantSummary = (variant, includeGenomeVersion) => (
  <div>
    {`${variant.chrom}:${variant.pos}`}
    {variant.alt && (
      <span>
        <SequenceContainer>{variant.ref}</SequenceContainer>
        <Icon fitted name="angle right" />
        <SequenceContainer>{variant.alt}</SequenceContainer>
      </span>
    )}
    {includeGenomeVersion && variant.genomeVersion && (
      <NoEmphasis>{`(${GENOME_VERSION_DISPLAY_LOOKUP[variant.genomeVersion] || variant.genomeVersion})`}</NoEmphasis>
    )}
  </div>
)

const BaseSubmissionGeneVariants = React.memo(({ geneVariants, modalId, genesById, dispatch, ...listProps }) => (
  <List {...listProps}>
    {Object.entries(geneVariants.reduce(
      (acc, variant) => ({ ...acc, [variant.geneId]: [...(acc[variant.geneId] || []), variant] }), {},
    )).map(([geneId, variants]) => (
      <TopAlignedItem key={geneId}>
        <ShowGeneModal gene={genesById[geneId]} modalId={modalId} />
        {variants.length > 0 && variants[0].pos && (
          <List.List>
            {variants.map((variant, i) => (
              <List.Item key={`${variant.pos}-${variant.ref}-${variant.alt}`}>
                {variantSummary(variant, (i + 1 === variants.length))}
              </List.Item>
            ))}
          </List.List>
        )}
      </TopAlignedItem>
    ))}
  </List>
))

BaseSubmissionGeneVariants.propTypes = {
  genesById: PropTypes.object,
  geneVariants: PropTypes.arrayOf(PropTypes.object),
  modalId: PropTypes.string,
  dispatch: PropTypes.func,
}

const mapGeneStateToProps = state => ({
  genesById: getGenesById(state),
})

export const SubmissionGeneVariants = connect(mapGeneStateToProps)(BaseSubmissionGeneVariants)

export const Phenotypes = React.memo(({ phenotypes, maxWidth, ...listProps }) => (
  <List bulleted {...listProps}>
    {phenotypes.map(phenotype => (
      <PhenotypeListItem key={phenotype.id} observed={phenotype.observed} maxWidth={maxWidth}>
        {`${phenotype.label} (${phenotype.id})`}
      </PhenotypeListItem>
    ))}
  </List>
))

Phenotypes.propTypes = {
  phenotypes: PropTypes.arrayOf(PropTypes.object),
  maxWidth: PropTypes.string,
}
