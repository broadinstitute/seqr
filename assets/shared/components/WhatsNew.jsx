import React from 'react'

module.exports = React.createClass({

    render: function() {
        return <table><tbody>
            <tr>
                <td><b>April 20, 2016</b><br/></td>
                <td>
                    <i class="fa fa-angle-double-right"></i> When a family's <i>solved</i> status is changed, the user and date when the change was made will now be shown on the Family page (similar to tags and notes)  <br/>
                    <i class="fa fa-angle-double-right"></i> Clicking 'Edit' on a family now allows 2 separate 'Details' fields to be entered: "Notes" and "Analysis Summary"<br/>
                    <i class="fa fa-angle-double-right"></i> Updated Clinvar and OMIM reference data

                </td>
            </tr>
            <tr>
            <td class="col-sm-2"><b>March 22, 2016</b><br/></td>
            <td><i class="fa fa-angle-double-right"></i> On the project page, a table near the bottom now shows a summary of the number of Phenotips terms entered. This table is only shown for accounts with 'manager' permissions on a project.<br/>
                <i class="fa fa-angle-double-right"></i> Ability to Edit or Delete tags on the project page<br/>
                <i class="fa fa-angle-double-right"></i> Bug fixes and backend updates (now using Django v1.9)<br/>
            </td>
        </tr>
        <tr>
            <td class="col-sm-2"><b>Feb 20, 2016</b><br/></td>
            <td>
                <i class="fa fa-angle-double-right"></i> For projects that have gene lists defined, Search For Causal Variants now supports filtering by gene lists through a drop-down that appears in the Location section under Genes.<br/>
                <i class="fa fa-angle-double-right"></i> Automatically-generated static pedigree images from <a href='http://haplopainter.sourceforge.net/'>HaploPainter</a> will now appear on the family pages for most multi-generation families.<br/>
                <i class="fa fa-angle-double-right"></i> Tags and notes can now be viewed separately for each family by using the new <a>All tags and notes for family</a> link on each family page.<br/>
                <i class="fa fa-angle-double-right"></i> Project, family, and gene search pages have been adjusted to improve usability.<br/>
                <i class="fa fa-angle-double-right"></i> The Clinvar reference dataset has been updated to the new <a href='ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/'>2/4/2016 Clinvar release.</a><br/><br/>
                <i class="fa fa-angle-double-right"></i> These features are being gradually added to projects over the next few weeks:<br/>
                - Integration with <a href='https://phenotips.org/'>PhenoTips™</a> for structured entry of patient phenotypes.<br/>
                - For projects that were sequenced at the Broad Institute, we have access to the underlying sequencing read data (.bam files) and will now
                be able to show an IGV-like view of the reads directly in the browser. This view will be accessible through a <sup><a class="view-reads">
                <img src='/images/igv_reads_12x12.png'/> &nbsp; SHOW READS</a></sup> icon that will appear next to each variant in the search results.<br/>
            </td>
        </tr>
        <tr>
            <td class="col-sm-2"><b>Previous</b><br/></td>
            <td>
                <i class="fa fa-angle-double-right"></i> When a variant falls in a gene that has multiple transcript isoforms, seqr selects only one of these transcripts
                to show in variant search results. The choice of transcript may affect things like whether the variant is labeled missense or splice-disrupting, as well as 'HGVSp' and other annotations.<br/>
                Before this update, seqr always chose the worst-affected transcript, but this sometimes led to obscure transcripts being shown for important disease genes. <br/>
                To avoid this, we've updated the transcript selection logic to:<br/>
                - ignore non-protein-coding transcripts (except when all transcripts for a given gene are non-protein-coding).<br/>
                - of the remaining transcripts, select the worst-affected transcripts for the given variant.<br/>
                - if there's a tie where multiple transcripts are worst-affected in the same way, see if any of them is canonical according to Gencode v19.
                If yes, use the canonical transcript. Otherwise, chose by alphabetical order of the transcript id.<br/>
                <br/>
                    <i class="fa fa-angle-double-right"></i> For De Novo Dominant variant searches on families that have data for mother, father and child,
                    more stringent filters are now applied as follows. A variant will only be shown if:<br/>
                    1) the read coverage in the child is no less than 10% of the total read coverage in the parents at the variant site<br/>
                    2) the variant GQ score is >= 20 in the child<br/>
                    3) the parents' variant call allele balance (number of reads supporting alt allele / total reads ) is less than 5%<br/>
                    - in this case, the setting from the adjustable Allele Balance slider is still applied, but only to the child, while the GQ slider value only applies to the parents.
                    <br/>
                        <i class="fa fa-angle-double-right"></i> Clicking on the variant effect (for example 'missense' in
                        <img width='15%' height='10%' style="position:relative; bottom:10px; padding-top:10px" src="{% static 'whatsnew/screenshot_20151210_variant_effect_link.png' %}" />)
                        brings up a popup dialog with all transcripts listed. After this update, the popup dialog will now show which of the transcripts
                        is canonical, and also the HGVSp for each.<br/>
                        <br/>
            </td>
        </tr>
        </tbody></table>
    }
});