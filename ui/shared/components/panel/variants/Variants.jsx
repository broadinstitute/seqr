import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid, Divider, Popup, Label, Button, Header } from 'semantic-ui-react'

import { CLINSIG_SEVERITY, getVariantMainGeneId } from 'shared/utils/constants'
import { TagFieldDisplay } from '../view-fields/TagFieldView'
import FamilyVariantReads from './FamilyVariantReads'
import FamilyVariantTags, { LoadedFamilyLabel, taggedByPopup } from './FamilyVariantTags'
import Annotations from './Annotations'
import Pathogenicity from './Pathogenicity'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantGenes, { VariantGene } from './VariantGene'
import VariantIndividuals from './VariantIndividuals'
import { VerticalSpacer } from '../../Spacers'


const StyledVariantRow = styled(({ isCompoundHet, ...props }) => <Grid.Row {...props} />)`  
  .column {
   ${(props => props.isCompoundHet) ? // eslint-disable-line  no-constant-condition
    '{ margin-top: 0em !important; margin-left: 1em !important; }' :
    '{ margin-top: 1em !important; margin-bottom: 0 !important; margin-left: 1em !important; }'}
  }
  
  padding: 0;
  color: #999;
  background-color: ${({ severity }) => {
    if (severity > 0) {
      return '#eaa8a857'
    } else if (severity === 0) {
      return '#f5d55c57'
    } else if (severity < 0) {
      return '#21a92624'
    }
    return 'inherit'
  }}
`

const StyledCompoundHetRows = styled(Grid)`
  margin-left: 0em !important;
  margin-right: 1em !important;
  margin-top: 0em !important;
  margin-bottom: 0 !important;
`

const InlinePopup = styled(Popup).attrs({ basic: true, flowing: true })`
  padding: 0.2em !important;
  box-shadow: none !important;
  z-index: 10 !important;
`

const tagFamily = tag =>
  <LoadedFamilyLabel
    familyGuid={tag.savedVariant.familyGuid}
    to={`/project/${tag.savedVariant.projectGuid}/saved_variants/variant/${tag.savedVariant.variantGuid}`}
    disableEdit
    target="_blank"
  />


const Variant = React.memo(({ variant, isCompoundHet, mainGeneId }) => {
  if (!mainGeneId) {
    mainGeneId = getVariantMainGeneId(variant)
  }
  const variantIndividuals = variant.familyGuids.map(familyGuid =>
    <VariantIndividuals key={familyGuid} familyGuid={familyGuid} variant={variant} isCompoundHet={isCompoundHet} />,
  )
  return (
    <StyledVariantRow key={variant.variant} severity={CLINSIG_SEVERITY[((variant.clinvar || {}).clinicalSignificance || '').toLowerCase()]} isCompoundHet >
      <Grid.Column width={16}>
        <Pathogenicity variant={variant} />
        {variant.discoveryTags && variant.discoveryTags.length > 0 &&
          <InlinePopup
            on="click"
            position="right center"
            trigger={<Button as={Label} basic color="grey">Other Project Discovery Tags</Button>}
            content={<TagFieldDisplay
              displayFieldValues={variant.discoveryTags}
              popup={taggedByPopup}
              tagAnnotation={tagFamily}
              displayAnnotationFirst
            />}
          />
      }
      </Grid.Column>
      {variant.familyGuids.map(familyGuid =>
        <Grid.Column key={familyGuid} width={16}>
          <FamilyVariantTags familyGuid={familyGuid} variant={variant} key={variant.variantId} isCompoundHet={isCompoundHet} />
        </Grid.Column>,
      )}
      <Grid.Column>
        {variant.svName && <Header size="medium" content={variant.svName} />}
        {!isCompoundHet && mainGeneId && <VariantGene geneId={mainGeneId} variant={variant} />}
        {!isCompoundHet && mainGeneId && Object.keys(variant.transcripts || {}).length > 1 && <Divider />}
        <VariantGenes mainGeneId={mainGeneId} variant={variant} />
        {isCompoundHet && Object.keys(variant.transcripts || {}).length > 1 && <VerticalSpacer height={20} />}
        {isCompoundHet && variantIndividuals}
      </Grid.Column>
      <Grid.Column><Annotations variant={variant} /></Grid.Column>
      <Grid.Column><Predictions variant={variant} /></Grid.Column>
      <Grid.Column><Frequencies variant={variant} /></Grid.Column>
      {!isCompoundHet &&
      <Grid.Column width={16}>
        {variantIndividuals}
      </Grid.Column>}
      <Grid.Column width={16}>
        <FamilyVariantReads variant={variant} />
      </Grid.Column>
    </StyledVariantRow>
  )
})

Variant.propTypes = {
  variant: PropTypes.object,
  isCompoundHet: PropTypes.bool,
  mainGeneId: PropTypes.string,
}


const CompoundHets = React.memo(({ variants, ...props }) => {
  const sharedGeneIds = Object.keys(variants[0].transcripts).filter(geneId => geneId in variants[1].transcripts)
  let mainGeneId = sharedGeneIds[0]
  if (sharedGeneIds.length > 1) {
    const mainGene1 = getVariantMainGeneId(variants[0])
    if (sharedGeneIds.includes(mainGene1)) {
      mainGeneId = mainGene1
    } else {
      const mainGene2 = getVariantMainGeneId(variants[1])
      if (sharedGeneIds.includes(mainGene2)) {
        mainGeneId = mainGene2
      }
    }
  }

  return (
    <StyledVariantRow>
      <VerticalSpacer height={16} />
      {variants[0].familyGuids.map(familyGuid =>
        <Grid.Column key={familyGuid} width={16}>
          <FamilyVariantTags familyGuid={familyGuid} variant={variants} />
        </Grid.Column>,
      )}
      <Grid.Column width={16}>
        {mainGeneId && <VariantGene geneId={mainGeneId} variant={variants[0]} areCompoundHets />}
      </Grid.Column>
      <StyledCompoundHetRows stackable columns="equal">
        {variants.map(compoundHet =>
          <Variant variant={compoundHet} key={compoundHet.variantId} mainGeneId={mainGeneId} isCompoundHet {...props} />,
        )}
      </StyledCompoundHetRows>
    </StyledVariantRow>
  )
})


CompoundHets.propTypes = {
  variants: PropTypes.array,
}

const Variants = React.memo(({ variants, ...props }) => (
  <Grid stackable divided="vertically" columns="equal">
    {variants.map(variant => (Array.isArray(variant) ?
      <CompoundHets variants={variant} key={`${variant.map(v => v.variantId).join()}-${variant[0].familyGuids.join('-')}`} {...props} /> :
      <Variant variant={variant} key={`${variant.variantId}-${variant.familyGuids.join('-')}`} {...props} />
    ))}
  </Grid>
))

Variants.propTypes = {
  variants: PropTypes.array,
}

export default Variants
