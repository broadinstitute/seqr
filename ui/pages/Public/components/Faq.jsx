/* eslint-disable react/jsx-one-expression-per-line */

import React from 'react'
import { Header, Segment, List, Icon } from 'semantic-ui-react'

import { WORKSPACE_REQUIREMENTS } from 'shared/components/panel/LoadWorkspaceDataForm'
import { SeqrAvailability } from './LandingPage'

export default () => (
  <Segment basic padded="very">
    <Header dividing content="FAQ" size="huge" />

    <Header content="Q. What is seqr?" size="medium" />
    seqr is an open source, Federal Information Security Management Act (FISMA) compliant genomic data analysis platform
    for rare disease diagnosis and gene discovery. The variant search interface is designed for family-based analyses.
    The seqr platform can load a joint called VCF and annotate it with relevant information for Mendelian analysis in a
    user-friendly web interface with links to external resources. Users can perform de novo/dominant, recessive
    (homozygous/compound heterozygous/X-linked), or custom searches (gene lists, incomplete penetrance, etc.) within a
    family to efficiently identify a diagnostic or candidate cause of disease among single nucleotide variants and
    indels. The platform supports searching a gene list across a group of samples. Through the Matchmaker Exchange
    interface, seqr also supports submission of candidate variants/genes and phenotypic information to an international
    network for gene discovery. <br /><br />

    To preview the functionality available in the seqr platform, please see our &nbsp;
    <a href="https://youtube.com/playlist?list=PLlMMtlgw6qNiY6mkBu111-lpmANKHdGKM" target="blank">tutorial videos</a>.

    <Header content="Q. What analyses are not supported in seqr?" size="medium" />
    <List bulleted>
      <List.Item>
        seqr is not designed for cohort or gene burden analyses. You can search for variants in a candidate gene across
        your data but seqr will not provide a quantification of how much variation you should expect to see.
      </List.Item>
      <List.Item>
        seqr is not an annotation pipeline for a VCF. While annotations are added when data is loaded in seqr, you
        cannot output the annotated VCF from seqr.
      </List.Item>
      <List.Item>
        seqr does not have reporting capabilities, although there is limited support for downloading short variant lists
        from seqr that could be used as input to generate a report externally.
      </List.Item>
    </List>

    <Header content="Q. Can I try out seqr?" size="medium" />
    Yes! Please create a seqr account and test out basic functionality using the demonstration project. <br /><br />

    The seqr login process requires that you register your email address in the NHGRI&quot;s Genomic Data Science
    Analysis, Visualization, and Informatics Lab-Space (AnVIL*). This requires a Google account, either a Gmail account
    or registering your non-Gmail email account with Google. <br /><br />

    Instructions to register using Gmail accounts or Google-registered email account:
    <List ordered>
      <List.Item>
        Go to <a href="https://anvil.terra.bio" target="blank">https://anvil.terra.bio</a>
      </List.Item>
      <List.Item>
        Open the hamburger menu ( <Icon name="bars" />) at the top left and click &quot;Sign In With Google&quot;.
        Sign in using the Gmail or Google-registered* email address you plan to use to log in to seqr
      </List.Item>
      <List.Item>
        You will be prompted to register and accept the AnVIL terms of service
      </List.Item>
      <List.Item>
        Go to <a href="https://seqr.broadinstitute.org" target="blank">https://seqr.broadinstitute.org</a> and confirm
        that you can log in. seqr will display a demo project that you are welcome to play around with to test how it
        works
      </List.Item>
    </List>

    *If you would prefer to use your institutional or other non-Gmail email address, you can follow &nbsp;
    <a href="https://anvilproject.org/learn/account-setup/obtaining-a-google-id" target="blank">this link</a> for
    instructions on how to create an account that is associated with your non-Gmail, institutional email address, then
    proceed with the instructions above.

    <Header content="Q. How can I analyze my data in seqr?" size="medium" />
    There are 3 mechanisms through which you can load and analyze your data in seqr:
    <SeqrAvailability hasFootnote />

    *AnVIL is a controlled-access NIH-designated data repository supported on the Terra platform. Users are expected to
    ensure that data use and sharing within a Terra or AnVIL Workspace are conducted in accordance with all applicable
    national, tribal, and state laws and regulations, as well as relevant institutional policies and procedures for
    handling genomic data. However, because seqr runs within Terra or AnVIL workspaces, no additional regulatory
    approval is required to use seqr to analyze data stored on Terra or AnVIL. <br />

    To learn more about generating a joint called vcf, please refer to
    this <a href="https://drive.google.com/file/d/1aE7vUvUOZw_r78Osjn1Q0Cs3c5DCuonz/view?usp=sharing" target="blank">documentation</a>

    <Header content="Q. How can I set up seqr locally?" size="medium" />
    Setting up seqr locally generally requires strong bioinformatics skills to deploy, and also requires the
    download/storage of large annotation datasets. There is <a href="https://github.com/broadinstitute/seqr/blob/master/deploy/LOCAL_INSTALL.md" target="blank">documentation</a>
    &nbsp; in GitHub on setting up a local instance of seqr. If you have questions or issues with deployment, we
    recommend you take a look at our <a href="https://github.com/broadinstitute/seqr/discussions" target="blank">Github discussions page</a>
    &nbsp; for general troubleshooting help. If after looking into our documentation, you still have questions that can
    not be easily answered via a discussion post, send us an <a href="mailto:seqr@broadinstitute.org">email</a>.

    <Header content="Q. I am unable to log in or access my project in seqr. What should I do?" size="medium" />
    To access seqr, users must have their email address registered with AnVIL (see instructions above) and to view
    specific projects they must have access to the AnVIL workspace corresponding to the project. The most frequent
    reason a user is unable to log in to a seqr project is because the email being used to log in is different from the
    one granted access to the project workspace. <br /><br />

    If you are still having trouble after you have confirmed your email address is registered with AnVIL and is the same
    as the one added to the seqr project, try the following:

    <List bulleted>
      <List.Item>
        <i>If you can not log into seqr at all:</i> Log into AnVIL first <a href="https://anvil.terra.bio" target="blank">here</a>
        &nbsp; and then proceed to <a href="https://seqr.broadinstitute.org" target="blank">seqr</a>.
      </List.Item>
      <List.Item>
        <i>If you do not see your project:</i> Log into AnVIL first <a href="https://anvil.terra.bio" target="blank">here</a>,
        navigate to the workspace associated with the project, then select &quot;Data&quot; &gt; &quot;Files&quot; &gt;
        &quot;Analyze in seqr&quot;.
      </List.Item>
    </List>

    <Header content="Q. How long does it take to load data in seqr?" size="medium" />
    Genomic datasets are large and the seqr loading pipeline richly annotates the variants so data loading can take from
    a few days to up to a week to process, depending on the sample numbers and data types.

    <Header content="Q. How do I add a new team member to a project?" size="medium" />
    To add a new collaborator, navigate to the respective workspace in AnVIL and select Share. Only personnel with
    &quot;Can Share&quot; level access in AnVIL can add or remove collaborators. The seqr team does not manage user
    access. <br /><br />

    Please make sure your new team member registers the same email with Terra/AnVIL as the one added to the workspace.
    This is the most frequent reason why new users are unable to access a project.

    <Header content="Q. What workspace permissions do I need to use seqr in AnVIL?" size="medium" />
    To access existing seqr projects, follow the above instructions for adding new collaborators. To submit a request to
    load data to seqr, you will need:

    <List bulleted>
      {WORKSPACE_REQUIREMENTS.map(item => <List.Item>{item}</List.Item>)}
    </List>

    If you do not have sufficient permissions on the workspace to request loading, you can contact the existing Owner of
    the workspace to request for these permissions. Another option is to clone the existing workspace and then request
    loading from the copy, as you will now be the Owner of the cloned workspace.

    <Header content="Q. How much does it cost to use seqr?" size="medium" />
    There are currently no costs associated with requests to load data from your AnVIL workspace to seqr or to use seqr
    in AnVIL to analyze genomic data. <br /><br />

    You will be responsible for the costs of storing your VCFs in an AnVIL workspace and will be responsible for any
    compute operations you choose to run in that workspace, including the cost for generating any joint called VCFs.
    You can find detailed information on AnVIL costs and billing &nbsp;
    <a href="https://support.terra.bio/hc/en-us/articles/360048632271-Overview-Terra-costs-and-billing-GCP-" target="blank">here</a>.
    Once it is confirmed that the data is accessible in seqr, the VCF can be removed from the AnVIL workspace.

    <Header content="Q. How do I add data to an existing project in seqr?" size="medium" />
    To add new data, create a new joint called VCF with all the samples you want in your seqr project, including those
    you had previously loaded, and upload it using the Load Additional Data feature on the Project Page. All notes and
    tags saved in previously analyzed cases will be kept.

    <Header content="Q. How do I transfer data between workspaces in seqr?" size="medium" />
    Each project in seqr is linked to a single workspace. We are unable to support loading a VCF from a new workspace
    to an existing seqr project. <br /><br />

    You can request to load a joint called VCF from a new workspace, which will create a new seqr project with the data.
    None of your previous analysis such as tags and notes will be available in this new project.
    Alternatively, if you want to add data to the existing project, you will need to move the new joint called VCF to
    the original workspace and request loading additional data from that project as described above.

    <Header content="Q. Have ideas for seqr?" size="medium" />
    We are excited to see seqr&apos;s features grow to support your and others analysis needs, and welcome your
    suggestions or code contributions to the open source project. Please open a new  &nbsp;
    <a href="https://github.com/broadinstitute/seqr/discussions" target="blank">Github discussion</a> to discuss your
    proposed ideas, or email us at <a href="mailto:seqr@broadinstitute.org">seqr@broadinstitute.org</a>.

  </Segment>
)
