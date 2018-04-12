import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import { HorizontalSpacer } from '../../Spacers'
import { BreakWord } from './Variants'

const uscBrowserLink = (variant, genomeVersion) => {
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
      <a href={uscBrowserLink(variant)} target="_blank"><b>chr{variant.chr}:{variant.pos}</b></a>
      <HorizontalSpacer width={10} />
      <BreakWord>{variant.ref}</BreakWord>
      <Icon name="angle right" style={{ marginRight: 0 }} />
      <BreakWord>{variant.alt}</BreakWord>
    </div>

    {variant.annotation && variant.annotation.rsid &&
      <div>
        <a href={`http://www.ncbi.nlm.nih.gov/SNP/snp_ref.cgi?searchType=adhoc_search&type=rs&rs=${variant.annotation.rsid}`} target="_blank" >
          {variant.annotations.rsid}
        </a>
      </div>
    }
    {variant.liftedOverGenomeVersion === '37' && variant.liftedOverChrom &&
      <div>
        <a href={uscBrowserLink(variant, '37')} target="_blank">
          hg19: chr{variant.liftedOverChrom}:{variant.liftedOverPos}
        </a>
      </div>
    }
    {variant.liftedOverGenomeVersion && !variant.liftedOverChrom && <div>hg19: liftover failed</div>}

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
