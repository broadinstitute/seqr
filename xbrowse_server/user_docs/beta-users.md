Beta Users Guide
================

### Becoming A Beta User

Please the xbrowse team at [xbrowse@broadinstitute.org](mailto://xbrowse@broadinstitute.org) if you would like to use 
xBrowse to analyze your data.
It is open to all researchers and there is no cost.
We'll just want to make sure that it actually makes sense to analyze your data in xBrowse.
So, in your email, please give us some quick background on what you want to analyze.

### Server Info

This Beta instance of xBrowse is accessible at [https://atgu.mgh.harvard.edu/xbrowse](https://atgu.mgh.harvard.edu/xbrowse).
The actual servers that host it are located at Massachusetts General Hospital.
For researchers within the Partners Health Care umbrella, data will be kept within the MGH network.
However, this Beta program is for research data, not clinical data - the servers are *not* HIPAA compliant.

As an aside, we take security very seriously with xBrowse.
We have built HIPAA-compliant websites before, and aim to make xBrowse every bit as secure as a production hospital application.
We are not pursuing HIPAA compliance at this time, because of the nature of beta software -
but we absolutely intend for xBrowse to be deployed in HIPAA- and CLIA- compliant pipelines in the near future.

### Uploading Data

During the Beta phase, users must transfer data manually -
we do not have an automatic upload process.
You can send data however you like, but the most common method is uploading to our FTP servers.
If that's easy, we'll just send you a unique username + password.

In order to use xBrowse, you need to upload two things: variant calls and pedigree data.

Variant calls should be in [VCF file format](http://www.1000genomes.org/wiki/Analysis/Variant%20Call%20Format/vcf-variant-call-format-version-41),
and can be whole genome, whole exome, or targeted sequencing data.

Pedigree data is most commonly uploaded via a [FAM](http://www.gwaspi.org/?page_id=671) file, but that is not required.
You can set pedigrees manually with the xBrowse GUI, though for larger projects that can be a bit unwieldy.

### Variant Calling

xBrowse does *not* perform any variant calling - it is a downstream analysis tool.
However, genome sequencing is not yet at a point where you can abstract analysis away from
sequencing or variant calling - it is still very important to analyze variants in the context of how they were called.

That is a long way of saying: your experience with xBrowse will be heavily dependent on how your data was generated.

Our group at ATGU has invested heavily in developing a robust variant calling pipeline (based on GATK and Picard) with 
partners at the Broad Institute.
In some cases, we can offer to *re-call* variants before they are uploaded to xBrowse.
This serves two purposes: data will be called via current best practices,
and it ensures that calls are generated in a similar manner to the reference samples that it will be compared to.
(However, it will not necessarily be *joint called* with them - that is still some time off.)

## Taking Full Advantage of xBrowse

We say above that xBrowse only requires variant calls and pedigrees.
That's for the minimal experience - but there is much more to xBrowse.

Have a look at the [feature reference](feature-reference) for a full breakdown -
but here are some questions for consideration:

**What other collaborators do you want to add?**

Go to the Manage Collaborators page - you can enter collaborators' emails there and they will be added to xBrowse

**Do you want to upload BAM files as well as VCF files?**

This will allow you to view exome coverage and visualize variant calls

**Do you have lists of known and/or candidate genes?**

If so, you should upload them as gene lists

**Do you have an additional reference panel to compare variants to?**

We can upload them for you, keeping them private to your project(s)

**Do you want to track variants in xBrowse?**

If so, be explicit! Tell all your collaborators to store interesting variants from the start,
and you'll have a constant reference page to look back at all your saved variants.

**Do you want to store phenotypes within xBrowse?**

This can be really convenient - though will depend on your current workflow.


FAQ
---

**Do you support upload formats other than VCF?**

No - but we're open to adding support for additional formats if it would be helpful. This just hasn't really been a need yet.

**Why can't I upload data over the web?**

This is an obvious feature request - to upload arbitrary new datasets.
We do plan to implement this eventually.

**How long does it take to upload data?**

Usually just a couple hours.
However, the upload process is somewhat rough around the edges now, and some datasets pose formatting issues, etc.
So there unfortunately is a long tail of upload times.