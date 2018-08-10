from collections import defaultdict
import logging
import os
from tqdm import tqdm
from django.core.management.base import BaseCommand, CommandError

from reference_data.management.commands.utils.download_utils import download_file
from reference_data.models import dbNSFPGene, GeneInfo

logger = logging.getLogger(__name__)

DBNSFP_GENE_URL = "http://storage.googleapis.com/seqr-reference-data/dbnsfp/dbNSFP3.5_gene"

class Command(BaseCommand):
    help ="Loads the dbNSFP_gene table (see https://sites.google.com/site/jpopgen/dbNSFP)"

    def add_arguments(self, parser):
        parser.add_argument('dbnsfp_gene_table', help="The dbNSFP gene table. Currently it's only available as part "
            "of the much larger dbNSFPv3.5a.zip download from https://sites.google.com/site/jpopgen/dbNSFP")

    def handle(self, *args, **options):
        update_dbnsfp_gene(options['dbnsfp_gene_table'])


def update_dbnsfp_gene(dbnsfp_gene_table_path=None):
    """
    Args:
        dbnsfp_gene_table_path (str): optional local dbNSFP_geen file path. If not specified, or the path doesn't exist,
            the table will be downloaded.
    """

    if GeneInfo.objects.count() == 0:
        raise CommandError("GeneInfo table is empty. Run './manage.py update_gencode' before running this command.")

    if not dbnsfp_gene_table_path or not os.path.isfile(dbnsfp_gene_table_path):
        dbnsfp_gene_table_path = download_file(DBNSFP_GENE_URL)

    gene_id_to_gene_info = {g.gene_id: g for g in GeneInfo.objects.all().only('gene_id')}

    counters = defaultdict(int)
    records = []
    with open(dbnsfp_gene_table_path) as f:
        header = next(f).rstrip('\r\n').split('\t')
        logger.info("Header: ")
        logger.info(", ".join(header))
        logger.info("Parsing gene records from {}".format(dbnsfp_gene_table_path))

        dbNSFPGene.objects.all().delete()

        for line in tqdm(f, unit=' genes'):
            counters['total'] += 1
            fields = line.rstrip('\r\n').split('\t')

            fields = dict(zip(header, fields))

            gene_id = fields['Ensembl_gene']
            if gene_id == ".":
                continue

            gene = gene_id_to_gene_info.get(gene_id)
            if not gene:
                logger.warn(("dbNSFP gene id '{}' not found in GeneInfo table. "
                    "Running ./manage.py update_gencode to update the gencode version might fix this. "
                    "Full dbNSFP record: {}").format(gene_id, fields))
                continue

            records.append({
                "gene": gene,
                "uniprot_acc": fields['Uniprot_acc'],
                "uniprot_id": fields['Uniprot_id'],
                "entrez_gene_id": fields['Entrez_gene_id'],
                "ccds_id": fields['CCDS_id'],
                "refseq_id": fields["Refseq_id"],
                "ucsc_id": fields['ucsc_id'],
                "pathway_uniprot": fields['Pathway(Uniprot)'],
                "pathway_biocarta_short": fields['Pathway(BioCarta)_short'],  #  Short name of the Pathway(s) the gene belongs to (from BioCarta)
                "pathway_biocarta_full": fields['Pathway(BioCarta)_full'],    #  Full name(s) of the Pathway(s) the gene belongs to (from BioCarta)
                "pathway_consensus_path_db": fields['Pathway(ConsensusPathDB)'],   # Pathway(s) the gene belongs to (from ConsensusPathDB)
                "pathway_kegg_id": fields['Pathway(KEGG)_id'],           # ID(s) of the Pathway(s) the gene belongs to (from KEGG)
                "pathway_kegg_full": fields['Pathway(KEGG)_full'],         # Full name(s) of the Pathway(s) the gene belongs to (from KEGG)
                "function_desc": fields['Function_description'].replace("FUNCTION: ", ""),  # Function description of the gene (from Uniprot)
                "disease_desc": fields['Disease_description'].replace("FUNCTION: ", ""),    # Disease(s) the gene caused or associated with (from Uniprot)
                "trait_association_gwas": fields['Trait_association(GWAS)'], # Trait(s) the gene associated with (from GWAS catalog)
                "go_biological_process": fields['GO_biological_process'],   # GO terms for biological process
                "go_cellular_component": fields['GO_cellular_component'],   # GO terms for cellular component
                "go_molecular_function": fields['GO_molecular_function'],   # GO terms for molecular function
                "tissue_specificity": fields['Tissue_specificity(Uniprot)'],   # Tissue specificity description from Uniprot
                "expression_egenetics": fields['Expression(egenetics)'],   # Tissues/organs the gene expressed in (egenetics data from BioMart)
                "expression_gnf_atlas": fields['Expression(GNF/Atlas)'],   # Tissues/organs the gene expressed in (GNF/Atlas data from BioMart)
                "rvis_exac": fields['RVIS_ExAC'],
                "ghis": fields['GHIS'],
                "essential_gene": fields['Essential_gene'],   # Essential ("E") or Non-essential phenotype-changing ("N") based on Mouse Genome Informatics database. from doi:10.1371/journal.pgen.1003484
                "mgi_mouse_gene": fields['MGI_mouse_gene'],   # Homolog mouse gene name from MGI
                "mgi_mouse_phenotype": fields['MGI_mouse_phenotype'],   # Phenotype description for the homolog mouse gene from MGI
                "zebrafish_gene": fields['ZFIN_zebrafish_gene'],   # Homolog zebrafish gene name from ZFIN
                "zebrafish_structure": fields['ZFIN_zebrafish_structure'],   # Affected structure of the homolog zebrafish gene from ZFIN
                "zebrafish_phenotype_quality": fields['ZFIN_zebrafish_phenotype_quality'],   # Phenotype description for the homolog zebrafish gene from ZFIN
                "zebrafish_phenotype_tag": fields['ZFIN_zebrafish_phenotype_tag'],   # Phenotype tag for the homolog zebrafish gene from ZFIN
            })

    print("Parsed {} records. Inserting them into dbNSFPGene".format(len(records)))

    dbNSFPGene.objects.bulk_create((dbNSFPGene(**record) for record in tqdm(records, unit=' genes')), batch_size=1000)

    logger.info("Done loading {} records into dbNSFPGene".format(dbNSFPGene.objects.count()))


"""
Columns of dbNSFP_gene:  (from dbNSFP REAMDE v3.5a)

	Gene_name: Gene symbol from HGNC
	Ensembl_gene: Ensembl gene id (from HGNC)
	chr: Chromosome number (from HGNC)
246	Gene_old_names: Old gene symbol (from HGNC)
247	Gene_other_names: Other gene names (from HGNC)
248	Uniprot_acc(HGNC/Uniprot): Uniprot acc number (from HGNC and Uniprot)
249	Uniprot_id(HGNC/Uniprot): Uniprot id (from HGNC and Uniprot)
250	Entrez_gene_id: Entrez gene id (from HGNC)
251	CCDS_id: CCDS id (from HGNC)
252	Refseq_id: Refseq gene id (from HGNC)
253	ucsc_id: UCSC gene id (from HGNC)
254	MIM_id: MIM gene id (from HGNC)
255	Gene_full_name: Gene full name (from HGNC)
256	Pathway(Uniprot): Pathway description from Uniprot
257	Pathway(BioCarta)_short: Short name of the Pathway(s) the gene belongs to (from BioCarta)
258	Pathway(BioCarta)_full: Full name(s) of the Pathway(s) the gene belongs to (from BioCarta)
259	Pathway(ConsensusPathDB): Pathway(s) the gene belongs to (from ConsensusPathDB)
260	Pathway(KEGG)_id: ID(s) of the Pathway(s) the gene belongs to (from KEGG)
261	Pathway(KEGG)_full: Full name(s) of the Pathway(s) the gene belongs to (from KEGG)
262	Function_description: Function description of the gene (from Uniprot)
263	Disease_description: Disease(s) the gene caused or associated with (from Uniprot)
264	MIM_phenotype_id: MIM id(s) of the phenotype the gene caused or associated with (from Uniprot)
265	MIM_disease: MIM disease name(s) with MIM id(s) in "[]" (from Uniprot)
266	Trait_association(GWAS): Trait(s) the gene associated with (from GWAS catalog)
267	GO_biological_process: GO terms for biological process
268	GO_cellular_component: GO terms for cellular component
269	GO_molecular_function: GO terms for molecular function
270	Tissue_specificity(Uniprot): Tissue specificity description from Uniprot
271	Expression(egenetics): Tissues/organs the gene expressed in (egenetics data from BioMart)
272	Expression(GNF/Atlas): Tissues/organs the gene expressed in (GNF/Atlas data from BioMart)
273	Interactions(IntAct): Other genes (separated by ;) this gene interacting with (from IntAct).
		Full information (gene name followed by Pubmed id in "[]") can be found in the ".complete"
		table
274	Interactions(BioGRID): Other genes (separated by ;) this gene interacting with (from BioGRID)
		Full information (gene name followed by Pubmed id in "[]") can be found in the ".complete"
		table
275	Interactions(ConsensusPathDB): Other genes (separated by ;) this gene interacting with
		(from ConsensusPathDB). Full information (gene name followed by Pubmed id in "[]") can be 
		found in the ".complete" table
276	P(HI): Estimated probability of haploinsufficiency of the gene
		(from doi:10.1371/journal.pgen.1001154)
277	P(rec): Estimated probability that gene is a recessive disease gene
		(from DOI:10.1126/science.1215040)
278	Known_rec_info: Known recessive status of the gene (from DOI:10.1126/science.1215040)
		"lof-tolerant = seen in homozygous state in at least one 1000G individual"
		"recessive = known OMIM recessive disease" 
		(original annotations from DOI:10.1126/science.1215040)
279	RVIS_EVS: Residual Variation Intolerance Score, a measure of intolerance of mutational burden,
		the higher the score the more tolerant to mutational burden the gene is. Based on EVS (ESP6500) data.
		from doi:10.1371/journal.pgen.1003709
280	RVIS_percentile_EVS: The percentile rank of the gene based on RVIS, the higher the percentile
		the more tolerant to mutational burden the gene is. Based on EVS (ESP6500) data.
281	LoF-FDR_ExAC: "A gene's corresponding FDR p-value for preferential LoF depletion among the ExAC population.
		Lower FDR corresponds with genes that are increasingly depleted of LoF variants." cited from RVIS document.
282	RVIS_ExAC: "ExAC-based RVIS; setting 'common' MAF filter at 0.05% in at least one of the six individual
		ethnic strata from ExAC." cited from RVIS document.
283	RVIS_percentile_ExAC: "Genome-Wide percentile for the new ExAC-based RVIS; setting 'common' MAF filter at 0.05%
		in at least one of the six individual ethnic strata from ExAC." cited from RVIS document.
284	GHIS: A score predicting the gene haploinsufficiency. The higher the score the more likely the gene is
		haploinsufficient. (from doi: 10.1093/nar/gkv474) 
285	ExAC_pLI: "the probability of being loss-of-function intolerant (intolerant of both heterozygous and 
		homozygous lof variants)" based on ExAC r0.3 data
286	ExAC_pRec: "the probability of being intolerant of homozygous, but not heterozygous lof variants"
		based on ExAC r0.3 data
287	ExAC_pNull: "the probability of being tolerant of both heterozygous and homozygous lof variants"
		based on ExAC r0.3 data
288	ExAC_nonTCGA_pLI: "the probability of being loss-of-function intolerant (intolerant of both heterozygous and 
		homozygous lof variants)" based on ExAC r0.3 nonTCGA subset
289	ExAC_nonTCGA_pRec: "the probability of being intolerant of homozygous, but not heterozygous lof variants"
		based on ExAC r0.3 nonTCGA subset
290	ExAC_nonTCGA_pNull: "the probability of being tolerant of both heterozygous and homozygous lof variants"
		based on ExAC r0.3 nonTCGA subset
291	ExAC_nonpsych_pLI: "the probability of being loss-of-function intolerant (intolerant of both heterozygous and 
		homozygous lof variants)" based on ExAC r0.3 nonpsych subset
292	ExAC_nonpsych_pRec: "the probability of being intolerant of homozygous, but not heterozygous lof variants"
		based on ExAC r0.3 nonpsych subset
293	ExAC_nonpsych_pNull: "the probability of being tolerant of both heterozygous and homozygous lof variants"
		based on ExAC r0.3 nonpsych subset
294	ExAC_del.score: "Winsorised deletion intolerance z-score" based on ExAC r0.3.1 CNV data
295	ExAC_dup.score: "Winsorised duplication intolerance z-score" based on ExAC r0.3.1 CNV data
296	ExAC_cnv.score: "Winsorised cnv intolerance z-score" based on ExAC r0.3.1 CNV data
297	ExAC_cnv_flag: "Gene is in a known region of recurrent CNVs mediated by tandem segmental duplications and
		intolerance scores are more likely to be biased or noisy." from ExAC r0.3.1 CNV release
298	GDI: gene damage index score, "a genome-wide, gene-level metric of the mutational damage that has
		accumulated in the general population" from doi: 10.1073/pnas.1518646112. The higher the score
		the less likely the gene is to be responsible for monogenic diseases.
299	GDI-Phred: Phred-scaled GDI scores
300	Gene damage prediction (all disease-causing genes): gene damage prediction (low/medium/high) by GDI
		for all diseases
301	Gene damage prediction (all Mendelian disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for all Mendelian diseases
302	Gene damage prediction (Mendelian AD disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for Mendelian autosomal dominant diseases
303	Gene damage prediction (Mendelian AR disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for Mendelian autosomal recessive diseases
304	Gene damage prediction (all PID disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for all primary immunodeficiency diseases
305	Gene damage prediction (PID AD disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for primary immunodeficiency autosomal dominant diseases
306	Gene damage prediction (PID AR disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for primary immunodeficiency autosomal recessive diseases
307	Gene damage prediction (all cancer disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for all cancer disease
308	Gene damage prediction (cancer recessive disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for cancer recessive disease
309	Gene damage prediction (cancer dominant disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for cancer dominant disease
310	LoFtool_score: a percential score for gene intolerance to functional change. The lower the score the higher
		gene intolerance to functional change. For details please contact Dr. Joao Fadista(joao.fadista@med.lu.se)
311	SORVA_LOF_MAF0.005_HetOrHom: the fraction of individuals in the 1000 Genomes Project data (N=2504)
		who are either Heterozygote or Homozygote of LOF SNVs whose MAF<0.005. This fraction is from 
		a method for ranking genes based on mutational burden called SORVA (Significance Of Rare VAriants). 
		Please see doi: 10.1101/103218 for details.
312	SORVA_LOF_MAF0.005_HomOrCompoundHet: the fraction of individuals in the 1000 Genomes Project data (N=2504)
		who are either Compound Heterozygote or Homozygote of LOF SNVs whose MAF<0.005. This fraction is from 
		a method for ranking genes based on mutational burden called SORVA (Significance Of Rare VAriants). 
		Please see doi: 10.1101/103218 for details.
313	SORVA_LOF_MAF0.001_HetOrHom: the fraction of individuals in the 1000 Genomes Project data (N=2504)
		who are either Heterozygote or Homozygote of LOF SNVs whose MAF<0.001. This fraction is from 
		a method for ranking genes based on mutational burden called SORVA (Significance Of Rare VAriants). 
		Please see doi: 10.1101/103218 for details.
314	SORVA_LOF_MAF0.001_HomOrCompoundHet: the fraction of individuals in the 1000 Genomes Project data (N=2504)
		who are either Compound Heterozygote or Homozygote of LOF SNVs whose MAF<0.001. This fraction is from 
		a method for ranking genes based on mutational burden called SORVA (Significance Of Rare VAriants). 
		Please see doi: 10.1101/103218 for details.
315	SORVA_LOForMissense_MAF0.005_HetOrHom: the fraction of individuals in the 1000 Genomes Project data (N=2504)
		who are either Heterozygote or Homozygote of LOF or missense SNVs whose MAF<0.005. This fraction is from 
		a method for ranking genes based on mutational burden called SORVA (Significance Of Rare VAriants). 
		Please see doi: 10.1101/103218 for details.
316	SORVA_LOForMissense_MAF0.005_HomOrCompoundHet: the fraction of individuals in the 1000 Genomes Project data (N=2504)
		who are either Compound Heterozygote or Homozygote of LOF or missense SNVs whose MAF<0.005. This fraction is from 
		a method for ranking genes based on mutational burden called SORVA (Significance Of Rare VAriants). 
		Please see doi: 10.1101/103218 for details.
317	SORVA_LOForMissense_MAF0.001_HetOrHom: the fraction of individuals in the 1000 Genomes Project data (N=2504)
		who are either Heterozygote or Homozygote of LOF or missense SNVs whose MAF<0.001. This fraction is from 
		a method for ranking genes based on mutational burden called SORVA (Significance Of Rare VAriants). 
		Please see doi: 10.1101/103218 for details.
318	SORVA_LOForMissense_MAF0.001_HomOrCompoundHet: the fraction of individuals in the 1000 Genomes Project data (N=2504)
		who are either Compound Heterozygote or Homozygote of LOF or missense SNVs whose MAF<0.001. This fraction is from 
		a method for ranking genes based on mutational burden called SORVA (Significance Of Rare VAriants). 
		Please see doi: 10.1101/103218 for details.
319	Essential_gene: Essential ("E") or Non-essential phenotype-changing ("N") based on
		Mouse Genome Informatics database. from doi:10.1371/journal.pgen.1003484
320	MGI_mouse_gene: Homolog mouse gene name from MGI
321	MGI_mouse_phenotype: Phenotype description for the homolog mouse gene from MGI
322	ZFIN_zebrafish_gene: Homolog zebrafish gene name from ZFIN
323	ZFIN_zebrafish_structure: Affected structure of the homolog zebrafish gene from ZFIN
324	ZFIN_zebrafish_phenotype_quality: Phenotype description for the homolog zebrafish gene
		from ZFIN
325	ZFIN_zebrafish_phenotype_tag: Phenotype tag for the homolog zebrafish gene from ZFIN
"""