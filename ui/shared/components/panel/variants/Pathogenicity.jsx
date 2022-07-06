import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Label, Icon } from 'semantic-ui-react'

import { getUser, getFamiliesByGuid, getProjectsByGuid } from 'redux/selectors'
import { CLINSIG_SEVERITY, getPermissionedHgmdClass } from '../../../utils/constants'
import { snakecaseToTitlecase } from '../../../utils/stringUtils'
import { HorizontalSpacer } from '../../Spacers'

const StarsContainer = styled.span`
  margin-left: 10px;
`

const StarIcon = styled(Icon).attrs({ name: 'star' })`
  color: ${props => (props.goldstar ? '#FFB70A' : '#D5D5D5')};
  margin: 0em 0.2em 0em 0em !important;
`

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

const ClinvarStars = React.memo(({ goldStars }) => goldStars != null && (
  <StarsContainer>
    {Array.from(Array(4).keys()).map(i => (i < goldStars ? <StarIcon key={i} goldstar="yes" /> : <StarIcon key={i} />))}
  </StarsContainer>
))

ClinvarStars.propTypes = {
  goldStars: PropTypes.number,
}

const PathogenicityLabel = React.memo(({ significance, formatName, goldStars }) => (
  <Label color={CLINSIG_COLOR[CLINSIG_SEVERITY[significance.toLowerCase()]] || 'grey'} size="medium" horizontal basic>
    {formatName ? formatName(significance) : significance}
    <ClinvarStars goldStars={goldStars} />
  </Label>
))

PathogenicityLabel.propTypes = {
  significance: PropTypes.string.isRequired,
  formatName: PropTypes.func,
  goldStars: PropTypes.number,
}

const PathogenicityLink = React.memo(({ href, ...labelProps }) => (
  <a href={href} target="_blank" rel="noreferrer">
    <PathogenicityLabel {...labelProps} />
    <HorizontalSpacer width={5} />
  </a>
))

PathogenicityLink.propTypes = {
  href: PropTypes.string.isRequired,
}

const clinvarUrl = (clinvar) => {
  const baseUrl = 'http://www.ncbi.nlm.nih.gov/clinvar'
  const variantPath = clinvar.alleleId ? `?term=${clinvar.alleleId}[alleleid]` : `/variation/${clinvar.variationId}`
  return baseUrl + variantPath
}

const Pathogenicity = React.memo(({ variant, showHgmd }) => {
  const clinvar = variant.clinvar || {}
  const pathogenicity = []
  if (clinvar.clinicalSignificance && (clinvar.variationId || clinvar.alleleId)) {
    pathogenicity.push(['ClinVar', {
      significance: clinvar.clinicalSignificance,
      href: clinvarUrl(clinvar),
      formatName: snakecaseToTitlecase,
      goldStars: clinvar.goldStars,
    }])
  }
  if (showHgmd) {
    pathogenicity.push(['HGMD', {
      significance: variant.hgmd.class,
      href: `https://my.qiagendigitalinsights.com/bbp/view/hgmd/pro/mut.php?acc=${variant.hgmd.accession}`,
      formatName: hgmdName,
    }])
  }
  if (variant.mitomapPathogenic) {
    pathogenicity.push(['MITOMAP', {
      significance: 'pathogenic',
      href: 'https://www.mitomap.org/foswiki/bin/view/MITOMAP/ConfirmedMutations',
    }])
  }

  return pathogenicity.map(([title, linkProps], index) => (
    <span key={title}>
      {!!index && <HorizontalSpacer width={5} />}
      <b>{`${title}:`}</b>
      <HorizontalSpacer width={5} />
      <PathogenicityLink {...linkProps} />
    </span>
  ))
})

Pathogenicity.propTypes = {
  variant: PropTypes.object,
  showHgmd: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  showHgmd: !!getPermissionedHgmdClass(
    ownProps.variant, getUser(state), getFamiliesByGuid(state), getProjectsByGuid(state),
  ),
})

export { Pathogenicity as BasePathogenicity }

export default connect(mapStateToProps)(Pathogenicity)
