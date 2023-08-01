import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Label, Icon, Popup } from 'semantic-ui-react'

import { getUser, getFamiliesByGuid, getProjectsByGuid } from 'redux/selectors'
import { clinvarSignificance, clinvarColor, getPermissionedHgmdClass } from '../../../utils/constants'
import { snakecaseToTitlecase } from '../../../utils/stringUtils'
import { HorizontalSpacer } from '../../Spacers'

const StarsContainer = styled.span`
  margin-left: 10px;
`

const StarIcon = styled(Icon).attrs({ name: 'star' })`
  color: ${props => (props.goldstar ? '#FFB70A' : '#D5D5D5')};
  margin: 0em 0.2em 0em 0em !important;
`

const HGMD_CLASS_NAMES = {
  DM: 'Disease Causing (DM)',
  'DM?': 'Disease Causing? (DM?)',
  FPV: 'Frameshift or truncating variant (FTV)',
  FP: 'In vitro/laboratory or in vivo functional polymorphism (FP)',
  DFP: 'Disease-associated polymorphism with additional supporting functional evidence (DFP)',
  DP: 'Disease-associated polymorphism (DP)',
}

const ClinvarStars = React.memo(({ goldStars }) => goldStars != null && (
  <StarsContainer>
    {Array.from(Array(4).keys()).map(i => (i < goldStars ? <StarIcon key={i} goldstar="yes" /> : <StarIcon key={i} />))}
  </StarsContainer>
))

ClinvarStars.propTypes = {
  goldStars: PropTypes.number,
}

const PathogenicityLabel = React.memo(({ label, color, goldStars }) => (
  <Label color={color || 'grey'} size="medium" horizontal basic>
    {label}
    <ClinvarStars goldStars={goldStars} />
  </Label>
))

PathogenicityLabel.propTypes = {
  label: PropTypes.string.isRequired,
  color: PropTypes.string,
  goldStars: PropTypes.number,
}

const PathogenicityLink = React.memo(({ href, popup, ...labelProps }) => {
  const link = (
    <a href={href} target="_blank" rel="noreferrer">
      <PathogenicityLabel {...labelProps} />
      <HorizontalSpacer width={5} />
    </a>
  )
  return popup ? <Popup trigger={link} content={popup} /> : link
})

PathogenicityLink.propTypes = {
  href: PropTypes.string.isRequired,
  popup: PropTypes.string,
}

const clinvarUrl = (clinvar) => {
  const baseUrl = 'http://www.ncbi.nlm.nih.gov/clinvar'
  const variantPath = clinvar.alleleId ? `?term=${clinvar.alleleId}[alleleid]` : `/variation/${clinvar.variationId}`
  return baseUrl + variantPath
}

const clinvarLabel = (pathogenicity, assertions, conflictingPathogenicities) => {
  let label = snakecaseToTitlecase(pathogenicity)
  if (conflictingPathogenicities && conflictingPathogenicities.length) {
    const conflictingLabels = conflictingPathogenicities.map(
      ({ pathogenicity: conflictingPath, count }) => `${snakecaseToTitlecase(conflictingPath)} (${count})`,
    )
    label = `${label} [${conflictingLabels.join('; ')}]`
  }
  if (assertions && assertions.length) {
    label = `${label} (${assertions.map(snakecaseToTitlecase).join(', ')})`
  }
  return label
}

const Pathogenicity = React.memo(({ variant, showHgmd }) => {
  const clinvar = variant.clinvar || {}
  const pathogenicity = []
  if ((clinvar.clinicalSignificance || clinvar.pathogenicity) && (clinvar.variationId || clinvar.alleleId)) {
    const { pathogenicity: clinvarPathogenicity, assertions, severity } = clinvarSignificance(clinvar)
    pathogenicity.push(['ClinVar', {
      label: clinvarLabel(clinvarPathogenicity, assertions, clinvar.conflictingPathogenicities),
      color: clinvarColor(severity, 'red', 'orange', 'green'),
      href: clinvarUrl(clinvar),
      goldStars: clinvar.goldStars,
      popup: clinvar.version && `Last Updated: ${new Date(clinvar.version).toLocaleDateString()}`,
    }])
  }
  if (showHgmd) {
    pathogenicity.push(['HGMD', {
      label: HGMD_CLASS_NAMES[variant.hgmd.class],
      href: `https://my.qiagendigitalinsights.com/bbp/view/hgmd/pro/mut.php?acc=${variant.hgmd.accession}`,
    }])
  }
  if (variant.mitomapPathogenic) {
    pathogenicity.push(['MITOMAP', {
      label: 'pathogenic',
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
