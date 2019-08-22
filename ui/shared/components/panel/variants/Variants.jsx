import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid, Divider } from 'semantic-ui-react'

import { CLINSIG_SEVERITY } from 'shared/utils/constants'
import FamilyVariantReads from './FamilyVariantReads'
import FamilyVariantTags from './FamilyVariantTags'
import Annotations from './Annotations'
import Pathogenicity from './Pathogenicity'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantGene from './VariantGene'
import VariantIndividuals from './VariantIndividuals'
import { VerticalSpacer } from '../../Spacers'


const StyledVariantRow = styled(Grid.Row)`
  .column {
    margin-top: 1em !important;
    margin-bottom: 0 !important;
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

const SingleVariant = ({ variant }) =>
  <StyledVariantRow key={variant.variantId} severity={CLINSIG_SEVERITY[(variant.clinvar.clinicalSignificance || '').toLowerCase()]}>
    <Grid.Column width={16}>
      <Pathogenicity variant={variant} />
    </Grid.Column>
    {variant.familyGuids.map(familyGuid =>
      <Grid.Column key={familyGuid} width={16}>
        <FamilyVariantTags familyGuid={familyGuid} variant={variant} />
      </Grid.Column>,
    )}
    <Grid.Column>
      {variant.mainTranscript.geneId && <VariantGene geneId={variant.mainTranscript.geneId} variant={variant} />}
      {Object.keys(variant.transcripts).length > 1 && <Divider />}
      {Object.keys(variant.transcripts).filter(geneId => geneId !== variant.mainTranscript.geneId).map(geneId =>
        <VariantGene key={geneId} geneId={geneId} variant={variant} compact />,
      )}
    </Grid.Column>
    <Grid.Column><Annotations variant={variant} /></Grid.Column>
    <Grid.Column><Predictions variant={variant} /></Grid.Column>
    <Grid.Column><Frequencies variant={variant} /></Grid.Column>
    <Grid.Column width={16}>
      {variant.familyGuids.map(familyGuid =>
        <VariantIndividuals key={familyGuid} familyGuid={familyGuid} variant={variant} />,
      )}
    </Grid.Column>
    <Grid.Column width={16}>
      <FamilyVariantReads variant={variant} />
    </Grid.Column>
  </StyledVariantRow>

SingleVariant.propTypes = {
  variant: PropTypes.object,
}

// const CompoundHet = ({ variant }) =>
//   <div>
//     <Grid.Column>
//       {Object.keys(variant.transcripts).filter(geneId => geneId !== variant.mainTranscript.geneId).map(geneId =>
//         <VariantGene key={geneId} geneId={geneId} variant={variant} compact />,
//       )}
//       {Object.keys(variant.transcripts).length > 1 && <VerticalSpacer height={20} />}
//       {variant.familyGuids.map(familyGuid =>
//         <VariantIndividuals key={familyGuid} familyGuid={familyGuid} variant={variant} />,
//       )}
//     </Grid.Column>
//     <Grid.Column><Annotations variant={variant} /></Grid.Column>
//     <Grid.Column><Predictions variant={variant} /></Grid.Column>
//     <Grid.Column><Frequencies variant={variant} /></Grid.Column>
//     <Grid.Column width={16}>
//       <FamilyVariantReads variant={variant} />
//     </Grid.Column>
//   </div>
//
// CompoundHet.prototype = {
//   variant: PropTypes.object,
// }

const CompoundHets = ({ variants }) =>
  <StyledVariantRow key={variants[0].variantId} severity={CLINSIG_SEVERITY[(variants[0].clinvar.clinicalSignificance || '').toLowerCase()]}>
    <Grid.Column width={16}>
      <Pathogenicity variant={variants[0]} />
    </Grid.Column>
    {variants[0].familyGuids.map(familyGuid =>
      <Grid.Column key={familyGuid} width={16}>
        <FamilyVariantTags familyGuid={familyGuid} variant={variants[0]} />
      </Grid.Column>,
    )}
    <Grid.Column width={16}>
      {variants[0].mainTranscript.geneId && <VariantGene geneId={variants[0].mainTranscript.geneId} variant={variants[0]} />}
    </Grid.Column>
    {/*<CompoundHet variant={variants[0]} />*/}
    <Grid.Column>
      {Object.keys(variants[0].transcripts).filter(geneId => geneId !== variants[0].mainTranscript.geneId).map(geneId =>
        <VariantGene key={geneId} geneId={geneId} variant={variants[0]} compact />,
      )}
      {Object.keys(variants[0].transcripts).length > 1 && <VerticalSpacer height={20} />}
      {variants[0].familyGuids.map(familyGuid =>
        <VariantIndividuals key={familyGuid} familyGuid={familyGuid} variant={variants[0]} />,
      )}
    </Grid.Column>
    <Grid.Column><Annotations variant={variants[0]} /></Grid.Column>
    <Grid.Column><Predictions variant={variants[0]} /></Grid.Column>
    <Grid.Column><Frequencies variant={variants[0]} /></Grid.Column>
    <Grid.Column width={16}>
      <FamilyVariantReads variant={variants[0]} />
    </Grid.Column>
    {/*<CompoundHet variant={variants[0]} />*/}
    <Grid.Column>
      {Object.keys(variants[1].transcripts).filter(geneId => geneId !== variants[0].mainTranscript.geneId).map(geneId =>
        <VariantGene key={geneId} geneId={geneId} variant={variants[1]} compact />,
      )}
      {Object.keys(variants[1].transcripts).length > 1 && <VerticalSpacer height={20} />}
      {variants[1].familyGuids.map(familyGuid =>
        <VariantIndividuals key={familyGuid} familyGuid={familyGuid} variant={variants[1]} />,
      )}
    </Grid.Column>
    <Grid.Column><Annotations variant={variants[1]} /></Grid.Column>
    <Grid.Column><Predictions variant={variants[1]} /></Grid.Column>
    <Grid.Column><Frequencies variant={variants[1]} /></Grid.Column>
    <Grid.Column width={16}>
      <FamilyVariantReads variant={variants[1]} />
    </Grid.Column>
  </StyledVariantRow>

CompoundHets.propTypes = {
  variants: PropTypes.object,
}

const Variants = ({ variants }) =>
  <Grid stackable divided="vertically" columns="equal">
    {variants.map(variant =>
      (variant.length > 1 ? <CompoundHets variants={variant} /> : <SingleVariant variant={variant} />))}
  </Grid>

Variants.propTypes = {
  variants: PropTypes.array,
}

export default Variants
