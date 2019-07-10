import React from 'react'
import { Header } from 'semantic-ui-react'

import { VerticalSpacer } from 'shared/components/Spacers'

export default () =>
  <div>
    <VerticalSpacer height={40} />
    <Header dividing content="Disclaimer" subheader="The Broad Institute Matchmaker Exchange" size="huge" />
    <VerticalSpacer height={10} />

    The data in Matchmaker Exchange is provided for research use only.<br /><br />

    Broad Institute provides the data in Matchmaker Exchange “as is”. Broad Institute makes no representations or
    warranties of any kind concerning the data, express or implied, including without limitation, warranties of
    merchantability, fitness for a particular purpose, noninfringement, or the absence of latent or other defects,
    whether or not discoverable. Broad will not be liable to the user or any third parties claiming through user, for
    any loss or damage suffered through the use of Matchmaker Exchange. In no event shall Broad Institute or its
    respective directors, officers, employees, affiliated investigators and affiliates be liable for indirect, special,
    incidental or consequential damages or injury to property and lost profits, regardless of whether the foregoing have
    been advised, shall have other reason to know, or in fact shall know of the possibility of the foregoing.
    <br /><br />

    Prior to using Broad Institute data in a publication, the user will contact the owner of the matching dataset to
    assess the integrity of the match. If the match is validated, the user will offer appropriate recognition of the
    data owner’s contribution, in accordance with academic standards and custom. Proper acknowledgment shall be made for
    the contributions of a party to such results being published or otherwise disclosed, which may include
    co-authorship.<br /><br />

    If Broad Institute contributes to the results being published, the authors must acknowledge Broad Institute using
    the following wording:
    <i>
      &nbsp;&#34;This study makes use of data shared through the Broad Institute matchbox repository. Funding for the
      Broad Institute was provided in part by National Institutes of Health grant UM1 HG008900 to Daniel MacArthur
      and Heidi Rehm.&#34;
    </i><br /><br />

    User will not attempt to use the data or Matchmaker Exchange to establish the individual identities of any of the
    subjects from whom the data were obtained. This applies to matches made within Broad Institute or with any other
    database included in the Matchmaker Exchange.
  </div>
