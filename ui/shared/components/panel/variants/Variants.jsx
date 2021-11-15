import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid, Divider, Popup, Label, Button, Header, Tab } from 'semantic-ui-react'

import { CLINSIG_SEVERITY, getVariantMainGeneId } from 'shared/utils/constants'
import { TagFieldDisplay } from '../view-fields/TagFieldView'
import FamilyReads from '../family/FamilyReads'
import FamilyVariantTags, { LoadedFamilyLabel, taggedByPopup } from './FamilyVariantTags'
import Annotations from './Annotations'
import Pathogenicity from './Pathogenicity'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantGenes, { VariantGene } from './VariantGene'
import VariantIndividuals from './VariantIndividuals'
import { compHetGene } from './VariantUtils'
import { VerticalSpacer } from '../../Spacers'
import AcmgModal from '../acmg/AcmgModal'

const StyledVariantRow = styled(({ isCompoundHet, isSV, severity, ...props }) => <Grid.Row {...props} />)`  
  .column {
   ${(props => props.isCompoundHet) ? // eslint-disable-line  no-constant-condition
    '{ margin-top: 0em !important; }' :
    '{ margin-top: 1em !important; margin-bottom: 0 !important; margin-left: 1em !important; }'}
  }
  
  padding: 0;
  color: #999;
  background-color: ${({ severity, isSV }) => {
    if (severity > 0) {
      return '#eaa8a857'
    }
    if (severity === 0) {
      return '#f5d55c57'
    }
    if (severity < 0) {
      return '#21a92624'
    }
    if (isSV) {
      return '#f3f8fa'
    }
    return 'inherit'
  }}
`

const StyledCompoundHetRows = styled(Grid)`
  margin-left: 1em !important;
  margin-right: 1em !important;
  margin-top: 0em !important;
  margin-bottom: 0 !important;
`

const InlinePopup = styled(Popup).attrs({ basic: true, flowing: true })`
  padding: 0.2em !important;
  box-shadow: none !important;
  z-index: 10 !important;
`

const NestedVariantTab = styled(Tab).attrs({
  menu: { fluid: true, vertical: true, secondary: true, pointing: true },
  grid: { paneWidth: 15, tabWidth: 1 },
  renderActiveOnly: false,
})`
  .segment.tab {
    margin: 0;
    &:first-child {
      padding: 0;
    }
  }
`

const tagFamily = tag => (
  <LoadedFamilyLabel
    familyGuid={tag.savedVariant.familyGuid}
    path={`saved_variants/variant/${tag.savedVariant.variantGuid}`}
    disableEdit
    target="_blank"
  />
)

const Variant = React.memo(({ variant, isCompoundHet, mainGeneId, linkToSavedVariants, reads, showReads }) => {
  const variantMainGeneId = mainGeneId || getVariantMainGeneId(variant)

  const severity = CLINSIG_SEVERITY[((variant.clinvar || {}).clinicalSignificance || '').toLowerCase()]
  return (
    <StyledVariantRow key={variant.variant} severity={severity} isSV={!!variant.svType} isCompoundHet>
      <Grid.Column width={16}>
        <Pathogenicity variant={variant} />
        {variant.discoveryTags && variant.discoveryTags.length > 0 && (
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
        )}
      </Grid.Column>
      {variant.familyGuids.map(familyGuid => (
        <Grid.Column key={familyGuid} width={16}>
          <FamilyVariantTags
            familyGuid={familyGuid}
            variant={variant}
            key={variant.variantId}
            isCompoundHet={isCompoundHet}
            linkToSavedVariants={linkToSavedVariants}
          />
        </Grid.Column>
      ))}
      <Grid.Column width={4}>
        {variant.svName && <Header size="medium" content={variant.svName} />}
        {!isCompoundHet && variantMainGeneId && <VariantGene geneId={variantMainGeneId} variant={variant} />}
        {!isCompoundHet && variantMainGeneId && Object.keys(variant.transcripts || {}).length > 1 && <Divider />}
        <VariantGenes mainGeneId={variantMainGeneId} variant={variant} />
        {isCompoundHet && Object.keys(variant.transcripts || {}).length > 1 && <VerticalSpacer height={20} />}
        {isCompoundHet && <VariantIndividuals variant={variant} isCompoundHet />}
        {isCompoundHet && showReads}
      </Grid.Column>
      <Grid.Column width={12}>
        <Grid columns="equal">
          <Grid.Row>
            <Grid.Column>
              <Annotations variant={variant} />
              { variant.variantGuid && <AcmgModal variant={variant} /> }
            </Grid.Column>
            <Grid.Column><Predictions variant={variant} /></Grid.Column>
            <Grid.Column><Frequencies variant={variant} /></Grid.Column>
          </Grid.Row>
          {!isCompoundHet && (
            <Grid.Row>
              <Grid.Column width={16}>
                <VariantIndividuals variant={variant} />
                {showReads}
              </Grid.Column>
            </Grid.Row>
          )}
        </Grid>
      </Grid.Column>
      <Grid.Column width={16}>
        {reads}
      </Grid.Column>
    </StyledVariantRow>
  )
})

Variant.propTypes = {
  variant: PropTypes.object,
  isCompoundHet: PropTypes.bool,
  mainGeneId: PropTypes.string,
  linkToSavedVariants: PropTypes.bool,
  reads: PropTypes.object,
  showReads: PropTypes.object,
}

const VariantWithReads = props => <FamilyReads layout={Variant} {...props} />

const compHetRows = (variants, mainGeneId, props) => variants.map(compoundHet => (
  <VariantWithReads
    variant={compoundHet}
    key={compoundHet.variantId}
    mainGeneId={mainGeneId}
    isCompoundHet
    {...props}
  />
))

const nestedVariantPanes = (variants, mainGeneId, props) => ([
  {
    menuIcon: 'plus',
    content: (
      <StyledCompoundHetRows stackable columns="equal">
        {compHetRows(variants, mainGeneId, props)}
      </StyledCompoundHetRows>
    ),
  },
  { menuIcon: 'minus', content: `Collapsing ${variants.length} nested variants` },
].map(({ menuIcon, content }, i) => ({
  menuItem: { key: menuIcon, icon: menuIcon },
  pane: { key: `pane${i}`, attached: false, basic: true, content },
})))

const CompoundHets = React.memo(({ variants, compoundHetToggle, ...props }) => {
  const mainGeneId = compHetGene(variants)

  // If linked variants are complex and not comp-het (more than 2 variants) and the first variant is a manual variant,
  // display associated variants nested under the manual variant
  const mainVariants = (variants.length > 2 && !variants[0].populations) && variants.splice(0, 1)
  const allVariants = [...(mainVariants || []), ...variants]

  return (
    <StyledVariantRow>
      <VerticalSpacer height={16} />
      {allVariants[0].familyGuids.map(familyGuid => (
        <Grid.Column key={familyGuid} width={16}>
          <FamilyVariantTags familyGuid={familyGuid} variant={allVariants} />
        </Grid.Column>
      ))}
      <Grid.Column width={16}>
        {mainGeneId && (
          <VariantGene
            geneId={mainGeneId}
            variant={allVariants[0]}
            areCompoundHets
            compoundHetToggle={compoundHetToggle}
          />
        )}
      </Grid.Column>
      <StyledCompoundHetRows stackable columns="equal">
        {compHetRows(mainVariants || variants, mainGeneId, props)}
      </StyledCompoundHetRows>
      {mainVariants && (
        <Grid.Column width={16}>
          <NestedVariantTab panes={nestedVariantPanes(variants, mainGeneId, props)} />
        </Grid.Column>
      )}
    </StyledVariantRow>
  )
})

CompoundHets.propTypes = {
  variants: PropTypes.arrayOf(PropTypes.object),
  compoundHetToggle: PropTypes.func,
}

const Variants = React.memo(({ variants, compoundHetToggle, ...props }) => (
  <Grid stackable divided="vertically">
    {variants.map(variant => (Array.isArray(variant) ?
      <CompoundHets variants={variant} key={`${variant.map(v => v.variantId).join()}-${variant[0].familyGuids.join('-')}`} compoundHetToggle={compoundHetToggle} {...props} /> :
      <VariantWithReads variant={variant} key={`${variant.variantId}-${variant.familyGuids.join('-')}`} {...props} />
    ))}
  </Grid>
))

Variants.propTypes = {
  variants: PropTypes.arrayOf(PropTypes.object),
  compoundHetToggle: PropTypes.func,
}

export default Variants
