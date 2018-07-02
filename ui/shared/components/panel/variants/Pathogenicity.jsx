import React from 'react'
import PropTypes from 'prop-types'
import { Grid, Label } from 'semantic-ui-react'

import { CLINSIG_SEVERITY } from '../../../utils/constants'
import { snakecaseToTitlecase } from '../../../utils/stringUtils'
import { HorizontalSpacer } from '../../Spacers'


const CLINSIG_COLOR = {
  1: 'red',
  0: 'orange',
  [-1]: 'green',
}

const HGMD_CLASS_NAMES = {
  DM: 'Disease Causing (DM)',
  'DM?': 'Disease Causing? (DM?)',
  FPV: 'Frameshift or truncating variant (FTV)',
  FP: 'In vitro/laboratory or in vivo functional polymorphism (FP)',
  DFP: 'Disease-associated polymorphism with additional supporting functional evidence (DFP)',
  DP: 'Disease-associated polymorphism (DP)',
}
const hgmdName = hgmdClass => HGMD_CLASS_NAMES[hgmdClass]


const PathogenicityLabel = ({ clinsig, formatName }) =>
  <Label color={CLINSIG_COLOR[CLINSIG_SEVERITY[clinsig]] || 'grey'} size="medium" horizontal basic>
    {formatName ? formatName(clinsig) : clinsig}
  </Label>

PathogenicityLabel.propTypes = {
  clinsig: PropTypes.string.isRequired,
  formatName: PropTypes.func,
}


const PathogenicityLink = ({ href, ...labelProps }) =>
  <a target="_blank" href={href}>
    <PathogenicityLabel {...labelProps} />
    <HorizontalSpacer width={5} />
  </a>

PathogenicityLink.propTypes = {
  href: PropTypes.string.isRequired,
}


const Pathogenicity = ({ variant }) => {
  if (!variant.clinvar.variantId && !variant.hgmd.class) {
    return null
  }

  return (
    <Grid.Column width={16}>
      {variant.clinvar.clinsig &&
        <span>
          <b>ClinVar:<HorizontalSpacer width={5} /></b>
          {variant.clinvar.clinsig.split('/').map(clinsig =>
            <PathogenicityLink
              key={clinsig}
              clinsig={clinsig}
              href={`http://www.ncbi.nlm.nih.gov/clinvar/variation/${variant.clinvar.variantId}`}
              formatName={snakecaseToTitlecase}
            />,
          )}
        </span>
      }
      {variant.hgmd.class &&
        <span>
          <HorizontalSpacer width={5} />
          <b>HGMD:<HorizontalSpacer width={5} /></b>
          <PathogenicityLink
            clinsig={variant.hgmd.class}
            href={`https://portal.biobase-international.com/hgmd/pro/mut.php?acc=${variant.hgmd.accession}`}
            formatName={hgmdName}
          />
        </span>
      }
    </Grid.Column>
  )
}

Pathogenicity.propTypes = {
  variant: PropTypes.object,
}


export default Pathogenicity
