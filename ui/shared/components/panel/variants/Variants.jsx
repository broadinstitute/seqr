import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid, Popup, Label, Button, Header, Tab } from 'semantic-ui-react'

import { GENOME_VERSION_37, clinvarSignificance, clinvarColor, getVariantMainGeneId } from 'shared/utils/constants'
import { VerticalSpacer } from '../../Spacers'
import { TagFieldDisplay } from '../view-fields/TagFieldView'
import FamilyReads from '../family/FamilyReads'
import FamilyVariantTags, { LoadedFamilyLabel, taggedByPopup } from './FamilyVariantTags'
import Annotations from './Annotations'
import Pathogenicity from './Pathogenicity'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantGenes, { VariantGene } from './VariantGene'
import VariantIndividuals from './VariantIndividuals'
import { compHetGene, has37Coords } from './VariantUtils'

export const StyledVariantRow = styled(({ isSV, severity, ...props }) => <Grid.Row {...props} />)`  
  .column {
    margin-top: 0em !important;
    margin-bottom: 0em !important;
  }
  
  color: #999;
  background-color: ${({ severity, isSV }) => {
    if (severity !== undefined) {
      return clinvarColor(severity, '#eaa8a857', '#f5d55c57', '#21a92624') || 'inherit'
    }
    if (isSV) {
      return '#f3f8fa'
    }
    return 'inherit'
  }}
`

const StyledCompoundHetRows = styled(Grid)`
  margin-top: 0em !important;
  margin-bottom: 0em !important;
  
  >.row {
    padding-bottom: 0 !important;
    &:first-child {
      padding-top: 0 !important;
    }
  }
`

const InlinePopup = styled(Popup).attrs({ basic: true, flowing: true })`
  padding: 0.2em !important;
  box-shadow: none !important;
  z-index: 10 !important;
`

const NestedVariantTab = styled(Tab).attrs({
  menu: { fluid: true, vertical: true, secondary: true, pointing: true },
  grid: { paneWidth: 12, tabWidth: 4 },
  defaultActiveIndex: 1,
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

const VariantLayout = (
  {
    variant, compoundHetToggle, mainGeneId, isCompoundHet, linkToSavedVariants, topContent,
    bottomContent, children, ...rowProps
  },
) => {
  const coreVariant = Array.isArray(variant) ? variant[0] : variant
  const geneModalId = Array.isArray(variant) ? variant.map(({ variantId }) => variantId).join('_') : variant.variantId
  return (
    <StyledVariantRow {...rowProps}>
      <Grid.Column width={16}>
        {topContent}
      </Grid.Column>
      {coreVariant.familyGuids.map(familyGuid => (
        <Grid.Column key={familyGuid} width={16}>
          <FamilyVariantTags
            familyGuid={familyGuid}
            variant={variant}
            isCompoundHet={isCompoundHet}
            linkToSavedVariants={linkToSavedVariants}
          />
          <VerticalSpacer height={10} />
        </Grid.Column>
      ))}
      {!isCompoundHet && (
        <Grid.Column width={4}>
          {!mainGeneId && coreVariant.svName && <Header size="medium" content={coreVariant.svName} />}
          {mainGeneId ? (
            <VariantGene
              geneId={mainGeneId}
              geneModalId={geneModalId}
              variant={coreVariant}
              compoundHetToggle={compoundHetToggle}
            />
          ) : <VariantGenes variant={variant} />}
        </Grid.Column>
      )}
      <Grid.Column width={isCompoundHet ? 16 : 12}>
        {children}
      </Grid.Column>
      <Grid.Column width={16}>
        {bottomContent}
      </Grid.Column>
    </StyledVariantRow>
  )
}

VariantLayout.propTypes = {
  variant: PropTypes.any, // eslint-disable-line react/forbid-prop-types
  isCompoundHet: PropTypes.bool,
  mainGeneId: PropTypes.string,
  linkToSavedVariants: PropTypes.bool,
  compoundHetToggle: PropTypes.func,
  topContent: PropTypes.node,
  bottomContent: PropTypes.node,
  children: PropTypes.node,
}

export const Variant = React.memo((
  { variant, mainGeneId, reads, showReads, dispatch, isCompoundHet, updateReads, ...props },
) => {
  const variantMainGeneId = mainGeneId || getVariantMainGeneId(variant)
  const { severity } = clinvarSignificance(variant.clinvar)
  return (
    <VariantLayout
      severity={severity}
      isSV={!!variant.svType}
      variant={variant}
      mainGeneId={variantMainGeneId}
      topContent={
        <div>
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
        </div>
      }
      bottomContent={reads}
      isCompoundHet={isCompoundHet}
      {...props}
    >
      <Grid columns="equal">
        <Grid.Row>
          <Grid.Column>
            <Annotations variant={variant} mainGeneId={variantMainGeneId} showMainGene={isCompoundHet} />
          </Grid.Column>
          <Grid.Column><Predictions variant={variant} /></Grid.Column>
          <Grid.Column><Frequencies variant={variant} /></Grid.Column>
        </Grid.Row>
        <Grid.Row>
          <Grid.Column width={16}>
            <VariantIndividuals variant={variant} />
            {showReads}
          </Grid.Column>
        </Grid.Row>
      </Grid>
    </VariantLayout>
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
    content: compHetRows(variants, mainGeneId, props),
  },
  { menuIcon: 'minus', content: `Collapsing ${variants.length} nested variants` },
].map(({ menuIcon, content }, i) => ({
  menuItem: { key: menuIcon, icon: menuIcon },
  pane: { key: `pane${i}`, attached: false, basic: true, content },
})))

const getValidCompHetLinkVariantId = (variant) => {
  if (!has37Coords(variant) || !variant.populations.gnomad_exomes?.af || variant.svType) {
    return null
  }
  const { chrom, pos, ref, alt, genomeVersion, liftedOverPos } = variant
  return `${chrom}-${genomeVersion === GENOME_VERSION_37 ? pos : liftedOverPos}-${ref}-${alt}`
}

const CompHetLink = ({ variants }) => {
  const varaintId1 = getValidCompHetLinkVariantId(variants[0])
  const varaintId2 = getValidCompHetLinkVariantId(variants[1])
  const href = `https://gnomad.broadinstitute.org/variant-cooccurrence?dataset=gnomad_r2_1&variant=${varaintId1}&variant=${varaintId2}`
  return varaintId1 && varaintId2 && <a href={href} target="_blank" rel="noreferrer">gnomAD Variant Co-Occurrence</a>
}

CompHetLink.propTypes = {
  variants: PropTypes.arrayOf(PropTypes.object),
}

const CompoundHets = React.memo(({ variants, compoundHetToggle, ...props }) => {
  // If linked variants are complex and not comp-het (more than 2 variants) and the first variant is a manual variant,
  // display associated variants nested under the manual variant
  const mainVariants = (variants.length > 2 && !variants[0].populations) && variants.slice(0, 1)

  const mainGeneId = compHetGene(variants) || (mainVariants && mainVariants[0].svName)

  return (
    <VariantLayout
      variant={variants}
      mainGeneId={mainGeneId}
      compoundHetToggle={compoundHetToggle}
      bottomContent={
        mainVariants && <NestedVariantTab panes={nestedVariantPanes(variants.slice(1), mainGeneId, props)} />
      }
    >
      <StyledCompoundHetRows>
        {variants.length === 2 && (
          <Grid.Row>
            <Grid.Column textAlign="right"><CompHetLink variants={variants} /></Grid.Column>
          </Grid.Row>
        )}
        {compHetRows(mainVariants || variants, mainGeneId, props)}
      </StyledCompoundHetRows>
    </VariantLayout>
  )
})

CompoundHets.propTypes = {
  variants: PropTypes.arrayOf(PropTypes.object),
  compoundHetToggle: PropTypes.func,
}

const Variants = React.memo(({ variants, compoundHetToggle, ...props }) => (
  <Grid stackable divided="vertically">
    {(variants || []).map(variant => (Array.isArray(variant) ?
      <CompoundHets variants={variant} key={`${variant.map(v => v.variantId).join()}-${variant[0].familyGuids.join('-')}`} compoundHetToggle={compoundHetToggle} {...props} /> :
      <VariantWithReads variant={variant} key={`${variant.variantId}-${variant.familyGuids.join('-')}`} {...props} />
    ))}
  </Grid>
))

Variants.propTypes = {
  variants: PropTypes.arrayOf(PropTypes.any),
  compoundHetToggle: PropTypes.func,
}

export default Variants
