import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Icon } from 'semantic-ui-react'

import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import ShowReadsButton from '../../buttons/ShowReadsButton'


const BreakWord = styled.span`
  word-break: break-all;
`

const LargeText = styled.div`
  font-size: 1.2em;
`

const locus = (variant, rangeSize) =>
  `chr${variant.chrom}:${variant.pos - rangeSize}-${variant.pos + rangeSize}`

const ucscBrowserLink = (variant, genomeVersion) => {
  /* eslint-disable space-infix-ops */
  genomeVersion = genomeVersion || variant.genomeVersion
  genomeVersion = genomeVersion === '37' ? '19' : genomeVersion
  const highlight = `hg${genomeVersion}.chr${variant.chrom}:${variant.pos}-${variant.pos + (variant.ref.length-1)}`
  const position = locus(variant, 10)
  return `http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg${genomeVersion}&highlight=${highlight}&position=${position}`
}

const VariantLocations = ({ variant }) =>
  <div>
    <LargeText>
      <a href={ucscBrowserLink(variant)} target="_blank" rel="noopener noreferrer"><b>{variant.chrom}:{variant.pos}</b></a>
      <HorizontalSpacer width={10} />
      <BreakWord>{variant.ref}</BreakWord>
      <Icon name="angle right" />
      <BreakWord>{variant.alt}</BreakWord>
    </LargeText>

    {variant.annotation && variant.annotation.rsid &&
      <div>
        <a href={`http://www.ncbi.nlm.nih.gov/SNP/snp_ref.cgi?searchType=adhoc_search&type=rs&rs=${variant.annotation.rsid}`} target="_blank" rel="noopener noreferrer">
          {variant.annotation.rsid}
        </a>
      </div>
    }
    {variant.liftedOverGenomeVersion === '37' && (
      variant.liftedOverPos ?
        <div>
          hg19:<HorizontalSpacer width={5} />
          <a href={ucscBrowserLink(variant, '37')} target="_blank" rel="noopener noreferrer">
            chr{variant.liftedOverChrom}:{variant.liftedOverPos}
          </a>
        </div>
        : <div>hg19: liftover failed</div>
      )
    }

    <VerticalSpacer height={10} />
    <ShowReadsButton familyGuid={variant.familyGuid} locus={locus(variant, 100)} />
  </div>

VariantLocations.propTypes = {
  variant: PropTypes.object,
}

export default VariantLocations
