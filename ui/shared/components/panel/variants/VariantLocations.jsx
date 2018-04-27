import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Icon } from 'semantic-ui-react'

import { HorizontalSpacer } from '../../Spacers'


const BreakWord = styled.span`
  word-break: break-all;
`

const ucscBrowserLink = (variant, genomeVersion) => {
  /* eslint-disable space-infix-ops */
  genomeVersion = genomeVersion || variant.genomeVersion
  genomeVersion = genomeVersion === '37' ? '19' : genomeVersion
  const highlight = `hg${genomeVersion}.chr${variant.chrom}:${variant.pos}-${variant.pos + (variant.ref.length-1)}`
  const position = `chr${variant.chrom}:${variant.pos-10}-${variant.pos+10}`
  return `http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg${genomeVersion}&highlight=${highlight}&position=${position}`
}

const VariantLocations = ({ variant }) =>
  <div>
    <div style={{ fontSize: '16px' }}>
      <a href={ucscBrowserLink(variant)} target="_blank"><b>chr{variant.chrom}:{variant.pos}</b></a>
      <HorizontalSpacer width={10} />
      <BreakWord>{variant.ref}</BreakWord>
      <Icon name="angle right" style={{ marginRight: 0 }} />
      <BreakWord>{variant.alt}</BreakWord>
    </div>

    {variant.annotation && variant.annotation.rsid &&
      <div>
        <a href={`http://www.ncbi.nlm.nih.gov/SNP/snp_ref.cgi?searchType=adhoc_search&type=rs&rs=${variant.annotation.rsid}`} target="_blank" >
          {variant.annotation.rsid}
        </a>
      </div>
    }
    {variant.liftedOverGenomeVersion === '37' && (
      variant.liftedOverPos ?
        <div>
          hg19:<HorizontalSpacer width={5} />
          <a href={ucscBrowserLink(variant, '37')} target="_blank">
            chr{variant.liftedOverChrom}:{variant.liftedOverPos}
          </a>
        </div>
        : <div>hg19: liftover failed</div>
      )
    }

    {(variant.family_read_data_is_available || true) &&
      //TODO correct conditional check?
      //TODO actually show on click
      <div><a><Icon name="options" /> SHOW READS</a></div>
     }
  </div>

VariantLocations.propTypes = {
  variant: PropTypes.object,
}

export default VariantLocations
