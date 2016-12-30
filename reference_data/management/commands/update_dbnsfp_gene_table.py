import os
from collections import defaultdict
from tqdm import tqdm
from django.core.management.base import BaseCommand

from reference_data.models import dbNSFPGene

class Command(BaseCommand):
    """This command updates the dbNSFP gene table. See https://sites.google.com/site/jpopgen/dbNSFP
    for more details.
    """

    def add_arguments(self, parser):
        parser.add_argument('dbnsfp_gene_table', help="The dbNSFP gene table")

    def handle(self, *args, **options):
        dbnsfp_gene_table_path = options['dbnsfp_gene_table']
        if not os.path.isfile(dbnsfp_gene_table_path):
            raise ValueError("File not found: %s" % dbnsfp_gene_table_path)

        counters = defaultdict(int)
        with open(dbnsfp_gene_table_path) as f:
            header = next(f).rstrip('\n').split('\t')
            #pprint(list(enumerate(header)))
            for line in tqdm(f, unit=' genes'):
                counters['total'] += 1
                fields = line.rstrip('\n').split('\t')

                record = dict(zip(header, fields))
                dbNSFPGene.objects.create(
                    gene_id=record['Ensembl_gene'],
                    refseq_id=record['Refseq_id'],
                    pathway_uniprot=record['Pathway(Uniprot)'],
                    pathway_biocarta_short=record['Pathway(BioCarta)_short'],  #  Short name of the Pathway(s) the gene belongs to (from BioCarta)
                    pathway_biocarta_full=record['Pathway(BioCarta)_full'],    #  Full name(s) of the Pathway(s) the gene belongs to (from BioCarta)
                    pathway_consensus_path_db=record['Pathway(ConsensusPathDB)'],   # Pathway(s) the gene belongs to (from ConsensusPathDB)
                    pathway_kegg_id=record['Pathway(KEGG)_id'],           # ID(s) of the Pathway(s) the gene belongs to (from KEGG)
                    pathway_kegg_full=record['Pathway(KEGG)_full'],         # Full name(s) of the Pathway(s) the gene belongs to (from KEGG)
                    function_desc=record['Function_description'].replace("FUNCTION: ", ""),  # Function description of the gene (from Uniprot)
                    disease_desc=record['Disease_description'].replace("FUNCTION: ", ""),    # Disease(s) the gene caused or associated with (from Uniprot)
                    trait_association_gwas=record['Trait_association(GWAS)'], # Trait(s) the gene associated with (from GWAS catalog)
                    go_biological_process=record['GO_biological_process'],   # GO terms for biological process
                    go_cellular_component=record['GO_cellular_component'],   # GO terms for cellular component
                    go_molecular_function=record['GO_molecular_function'],   # GO terms for molecular function
                    tissue_specificity=record['Tissue_specificity(Uniprot)'],   # Tissue specificity description from Uniprot
                    expression_egenetics=record['Expression(egenetics)'],   # Tissues/organs the gene expressed in (egenetics data from BioMart)
                    expression_gnf_atlas=record['Expression(GNF/Atlas)'],   # Tissues/organs the gene expressed in (GNF/Atlas data from BioMart)
                    essential_gene=record['Essential_gene'],   # Essential ("E") or Non-essential phenotype-changing ("N") based on Mouse Genome Informatics database. from doi:10.1371/journal.pgen.1003484
                    mgi_mouse_gene=record['MGI_mouse_gene'],   # Homolog mouse gene name from MGI
                    mgi_mouse_phenotype=record['MGI_mouse_phenotype'],   # Phenotype description for the homolog mouse gene from MGI
                    zebrafish_gene=record['ZFIN_zebrafish_gene'],   # Homolog zebrafish gene name from ZFIN
                    zebrafish_structure=record['ZFIN_zebrafish_structure'],   # Affected structure of the homolog zebrafish gene from ZFIN
                    zebrafish_phenotype_quality=record['ZFIN_zebrafish_phenotype_quality'],   # Phenotype description for the homolog zebrafish gene from ZFIN
                    zebrafish_phenotype_tag=record['ZFIN_zebrafish_phenotype_tag'],   # Phenotype tag for the homolog zebrafish gene from ZFIN
                )

            print("Done inserting %s records." % str(counters['total']))


"""

Columns of dbNSFP_gene:  (from dbNSFP REAMDE)

	Gene_name: Gene symbol from HGNC
	Ensembl_gene: Ensembl gene id (from HGNC)
	chr: Chromosome number (from HGNC)
188	Gene_old_names: Old gene symbol (from HGNC)
189	Gene_other_names: Other gene names (from HGNC)
190	Uniprot_acc(HGNC/Uniprot): Uniprot acc number (from HGNC and Uniprot)
191	Uniprot_id(HGNC/Uniprot): Uniprot id (from HGNC and Uniprot)
192	Entrez_gene_id: Entrez gene id (from HGNC)
193	CCDS_id: CCDS id (from HGNC)
194	** Refseq_id: Refseq gene id (from HGNC)
195	ucsc_id: UCSC gene id (from HGNC)
196	MIM_id: MIM gene id (from HGNC)
197	Gene_full_name: Gene full name (from HGNC)
198	Pathway(Uniprot): Pathway description from Uniprot
199	Pathway(BioCarta)_short: Short name of the Pathway(s) the gene belongs to (from BioCarta)
200	Pathway(BioCarta)_full: Full name(s) of the Pathway(s) the gene belongs to (from BioCarta)
201	Pathway(ConsensusPathDB): Pathway(s) the gene belongs to (from ConsensusPathDB)
202	Pathway(KEGG)_id: ID(s) of the Pathway(s) the gene belongs to (from KEGG)
203	Pathway(KEGG)_full: Full name(s) of the Pathway(s) the gene belongs to (from KEGG)
204	Function_description: Function description of the gene (from Uniprot)
205	Disease_description: Disease(s) the gene caused or associated with (from Uniprot)
206	MIM_phenotype_id: MIM id(s) of the phenotype the gene caused or associated with (from Uniprot)
207	MIM_disease: MIM disease name(s) with MIM id(s) in "[]" (from Uniprot)
208	Trait_association(GWAS): Trait(s) the gene associated with (from GWAS catalog)
209	GO_biological_process: GO terms for biological process
210	GO_cellular_component: GO terms for cellular component
211	GO_molecular_function: GO terms for molecular function
212	Tissue_specificity(Uniprot): Tissue specificity description from Uniprot
213	Expression(egenetics): Tissues/organs the gene expressed in (egenetics data from BioMart)
214	Expression(GNF/Atlas): Tissues/organs the gene expressed in (GNF/Atlas data from BioMart)
215	Adipose-Subcutaneous minimum: minimum rpkm of GTEx V6 Adipose-Subcutaneous samples
216	Adipose-Subcutaneous maximum: minimum rpkm of GTEx V6 Adipose-Subcutaneous samples
217	Adipose-Subcutaneous average: minimum rpkm of GTEx V6 Adipose-Subcutaneous samples
218	Adipose-Subcutaneous nsample: number of GTEx V6 Adipose-Subcutaneous samples
219	Adipose-Visceral(Omentum) minimum: minimum rpkm of GTEx V6 Adipose-Visceral(Omentum) samples
220	Adipose-Visceral(Omentum) maximum: minimum rpkm of GTEx V6 Adipose-Visceral(Omentum) samples
221	Adipose-Visceral(Omentum) average: minimum rpkm of GTEx V6 Adipose-Visceral(Omentum) samples
222	Adipose-Visceral(Omentum) nsample: number of GTEx V6 Adipose-Visceral(Omentum) samples
223	AdrenalGland minimum: minimum rpkm of GTEx V6 AdrenalGland samples
224	AdrenalGland maximum: minimum rpkm of GTEx V6 AdrenalGland samples
225	AdrenalGland average: minimum rpkm of GTEx V6 AdrenalGland samples
226	AdrenalGland nsample: number of GTEx V6 AdrenalGland samples
227	Artery-Aorta minimum: minimum rpkm of GTEx V6 Artery-Aorta samples
228	Artery-Aorta maximum: minimum rpkm of GTEx V6 Artery-Aorta samples
229	Artery-Aorta average: minimum rpkm of GTEx V6 Artery-Aorta samples
230	Artery-Aorta nsample: number of GTEx V6 Artery-Aorta samples
231	Artery-Coronary minimum: minimum rpkm of GTEx V6 Artery-Coronary samples
232	Artery-Coronary maximum: minimum rpkm of GTEx V6 Artery-Coronary samples
233	Artery-Coronary average: minimum rpkm of GTEx V6 Artery-Coronary samples
234	Artery-Coronary nsample: number of GTEx V6 Artery-Coronary samples
235	Artery-Tibial minimum: minimum rpkm of GTEx V6 Artery-Tibial samples
236	Artery-Tibial maximum: minimum rpkm of GTEx V6 Artery-Tibial samples
237	Artery-Tibial average: minimum rpkm of GTEx V6 Artery-Tibial samples
238	Artery-Tibial nsample: number of GTEx V6 Artery-Tibial samples
239	Bladder minimum: minimum rpkm of GTEx V6 Bladder samples
240	Bladder maximum: minimum rpkm of GTEx V6 Bladder samples
241	Bladder average: minimum rpkm of GTEx V6 Bladder samples
242	Bladder nsample: number of GTEx V6 Bladder samples
243	Brain-Amygdala minimum: minimum rpkm of GTEx V6 Brain-Amygdala samples
244	Brain-Amygdala maximum: minimum rpkm of GTEx V6 Brain-Amygdala samples
245	Brain-Amygdala average: minimum rpkm of GTEx V6 Brain-Amygdala samples
246	Brain-Amygdala nsample: number of GTEx V6 Brain-Amygdala samples
247	Brain-Anteriorcingulatecortex(BA24) minimum: minimum rpkm of GTEx V6 Brain-Anteriorcingulatecortex(BA24) samples
248	Brain-Anteriorcingulatecortex(BA24) maximum: minimum rpkm of GTEx V6 Brain-Anteriorcingulatecortex(BA24) samples
249	Brain-Anteriorcingulatecortex(BA24) average: minimum rpkm of GTEx V6 Brain-Anteriorcingulatecortex(BA24) samples
250	Brain-Anteriorcingulatecortex(BA24) nsample: number of GTEx V6 Brain-Anteriorcingulatecortex(BA24) samples
251	Brain-Caudate(basalganglia) minimum: minimum rpkm of GTEx V6 Brain-Caudate(basalganglia) samples
252	Brain-Caudate(basalganglia) maximum: minimum rpkm of GTEx V6 Brain-Caudate(basalganglia) samples
253	Brain-Caudate(basalganglia) average: minimum rpkm of GTEx V6 Brain-Caudate(basalganglia) samples
254	Brain-Caudate(basalganglia) nsample: number of GTEx V6 Brain-Caudate(basalganglia) samples
255	Brain-CerebellarHemisphere minimum: minimum rpkm of GTEx V6 Brain-CerebellarHemisphere samples
256	Brain-CerebellarHemisphere maximum: minimum rpkm of GTEx V6 Brain-CerebellarHemisphere samples
257	Brain-CerebellarHemisphere average: minimum rpkm of GTEx V6 Brain-CerebellarHemisphere samples
258	Brain-CerebellarHemisphere nsample: number of GTEx V6 Brain-CerebellarHemisphere samples
259	Brain-Cerebellum minimum: minimum rpkm of GTEx V6 Brain-Cerebellum samples
260	Brain-Cerebellum maximum: minimum rpkm of GTEx V6 Brain-Cerebellum samples
261	Brain-Cerebellum average: minimum rpkm of GTEx V6 Brain-Cerebellum samples
262	Brain-Cerebellum nsample: number of GTEx V6 Brain-Cerebellum samples
263	Brain-Cortex minimum: minimum rpkm of GTEx V6 Brain-Cortex samples
264	Brain-Cortex maximum: minimum rpkm of GTEx V6 Brain-Cortex samples
265	Brain-Cortex average: minimum rpkm of GTEx V6 Brain-Cortex samples
266	Brain-Cortex nsample: number of GTEx V6 Brain-Cortex samples
267	Brain-FrontalCortex(BA9) minimum: minimum rpkm of GTEx V6 Brain-FrontalCortex(BA9) samples
268	Brain-FrontalCortex(BA9) maximum: minimum rpkm of GTEx V6 Brain-FrontalCortex(BA9) samples
269	Brain-FrontalCortex(BA9) average: minimum rpkm of GTEx V6 Brain-FrontalCortex(BA9) samples
270	Brain-FrontalCortex(BA9) nsample: number of GTEx V6 Brain-FrontalCortex(BA9) samples
271	Brain-Hippocampus minimum: minimum rpkm of GTEx V6 Brain-Hippocampus samples
272	Brain-Hippocampus maximum: minimum rpkm of GTEx V6 Brain-Hippocampus samples
273	Brain-Hippocampus average: minimum rpkm of GTEx V6 Brain-Hippocampus samples
274	Brain-Hippocampus nsample: number of GTEx V6 Brain-Hippocampus samples
275	Brain-Hypothalamus minimum: minimum rpkm of GTEx V6 Brain-Hypothalamus samples
276	Brain-Hypothalamus maximum: minimum rpkm of GTEx V6 Brain-Hypothalamus samples
277	Brain-Hypothalamus average: minimum rpkm of GTEx V6 Brain-Hypothalamus samples
278	Brain-Hypothalamus nsample: number of GTEx V6 Brain-Hypothalamus samples
279	Brain-Nucleusaccumbens(basalganglia) minimum: minimum rpkm of GTEx V6 Brain-Nucleusaccumbens(basalganglia) samples
280	Brain-Nucleusaccumbens(basalganglia) maximum: minimum rpkm of GTEx V6 Brain-Nucleusaccumbens(basalganglia) samples
281	Brain-Nucleusaccumbens(basalganglia) average: minimum rpkm of GTEx V6 Brain-Nucleusaccumbens(basalganglia) samples
282	Brain-Nucleusaccumbens(basalganglia) nsample: number of GTEx V6 Brain-Nucleusaccumbens(basalganglia) samples
283	Brain-Putamen(basalganglia) minimum: minimum rpkm of GTEx V6 Brain-Putamen(basalganglia) samples
284	Brain-Putamen(basalganglia) maximum: minimum rpkm of GTEx V6 Brain-Putamen(basalganglia) samples
285	Brain-Putamen(basalganglia) average: minimum rpkm of GTEx V6 Brain-Putamen(basalganglia) samples
286	Brain-Putamen(basalganglia) nsample: number of GTEx V6 Brain-Putamen(basalganglia) samples
287	Brain-Spinalcord(cervicalc-1) minimum: minimum rpkm of GTEx V6 Brain-Spinalcord(cervicalc-1) samples
288	Brain-Spinalcord(cervicalc-1) maximum: minimum rpkm of GTEx V6 Brain-Spinalcord(cervicalc-1) samples
289	Brain-Spinalcord(cervicalc-1) average: minimum rpkm of GTEx V6 Brain-Spinalcord(cervicalc-1) samples
290	Brain-Spinalcord(cervicalc-1) nsample: number of GTEx V6 Brain-Spinalcord(cervicalc-1) samples
291	Brain-Substantianigra minimum: minimum rpkm of GTEx V6 Brain-Substantianigra samples
292	Brain-Substantianigra maximum: minimum rpkm of GTEx V6 Brain-Substantianigra samples
293	Brain-Substantianigra average: minimum rpkm of GTEx V6 Brain-Substantianigra samples
294	Brain-Substantianigra nsample: number of GTEx V6 Brain-Substantianigra samples
295	Breast-MammaryTissue minimum: minimum rpkm of GTEx V6 Breast-MammaryTissue samples
296	Breast-MammaryTissue maximum: minimum rpkm of GTEx V6 Breast-MammaryTissue samples
297	Breast-MammaryTissue average: minimum rpkm of GTEx V6 Breast-MammaryTissue samples
298	Breast-MammaryTissue nsample: number of GTEx V6 Breast-MammaryTissue samples
299	Cells-EBV-transformedlymphocytes minimum: minimum rpkm of GTEx V6 Cells-EBV-transformedlymphocytes samples
300	Cells-EBV-transformedlymphocytes maximum: minimum rpkm of GTEx V6 Cells-EBV-transformedlymphocytes samples
301	Cells-EBV-transformedlymphocytes average: minimum rpkm of GTEx V6 Cells-EBV-transformedlymphocytes samples
302	Cells-EBV-transformedlymphocytes nsample: number of GTEx V6 Cells-EBV-transformedlymphocytes samples
303	Cells-Transformedfibroblasts minimum: minimum rpkm of GTEx V6 Cells-Transformedfibroblasts samples
304	Cells-Transformedfibroblasts maximum: minimum rpkm of GTEx V6 Cells-Transformedfibroblasts samples
305	Cells-Transformedfibroblasts average: minimum rpkm of GTEx V6 Cells-Transformedfibroblasts samples
306	Cells-Transformedfibroblasts nsample: number of GTEx V6 Cells-Transformedfibroblasts samples
307	Cervix-Ectocervix minimum: minimum rpkm of GTEx V6 Cervix-Ectocervix samples
308	Cervix-Ectocervix maximum: minimum rpkm of GTEx V6 Cervix-Ectocervix samples
309	Cervix-Ectocervix average: minimum rpkm of GTEx V6 Cervix-Ectocervix samples
310	Cervix-Ectocervix nsample: number of GTEx V6 Cervix-Ectocervix samples
311	Cervix-Endocervix minimum: minimum rpkm of GTEx V6 Cervix-Endocervix samples
312	Cervix-Endocervix maximum: minimum rpkm of GTEx V6 Cervix-Endocervix samples
313	Cervix-Endocervix average: minimum rpkm of GTEx V6 Cervix-Endocervix samples
314	Cervix-Endocervix nsample: number of GTEx V6 Cervix-Endocervix samples
315	Colon-Sigmoid minimum: minimum rpkm of GTEx V6 Colon-Sigmoid samples
316	Colon-Sigmoid maximum: minimum rpkm of GTEx V6 Colon-Sigmoid samples
317	Colon-Sigmoid average: minimum rpkm of GTEx V6 Colon-Sigmoid samples
318	Colon-Sigmoid nsample: number of GTEx V6 Colon-Sigmoid samples
319	Colon-Transverse minimum: minimum rpkm of GTEx V6 Colon-Transverse samples
320	Colon-Transverse maximum: minimum rpkm of GTEx V6 Colon-Transverse samples
321	Colon-Transverse average: minimum rpkm of GTEx V6 Colon-Transverse samples
322	Colon-Transverse nsample: number of GTEx V6 Colon-Transverse samples
323	Esophagus-GastroesophagealJunction minimum: minimum rpkm of GTEx V6 Esophagus-GastroesophagealJunction samples
324	Esophagus-GastroesophagealJunction maximum: minimum rpkm of GTEx V6 Esophagus-GastroesophagealJunction samples
325	Esophagus-GastroesophagealJunction average: minimum rpkm of GTEx V6 Esophagus-GastroesophagealJunction samples
326	Esophagus-GastroesophagealJunction nsample: number of GTEx V6 Esophagus-GastroesophagealJunction samples
327	Esophagus-Mucosa minimum: minimum rpkm of GTEx V6 Esophagus-Mucosa samples
328	Esophagus-Mucosa maximum: minimum rpkm of GTEx V6 Esophagus-Mucosa samples
329	Esophagus-Mucosa average: minimum rpkm of GTEx V6 Esophagus-Mucosa samples
330	Esophagus-Mucosa nsample: number of GTEx V6 Esophagus-Mucosa samples
331	Esophagus-Muscularis minimum: minimum rpkm of GTEx V6 Esophagus-Muscularis samples
332	Esophagus-Muscularis maximum: minimum rpkm of GTEx V6 Esophagus-Muscularis samples
333	Esophagus-Muscularis average: minimum rpkm of GTEx V6 Esophagus-Muscularis samples
334	Esophagus-Muscularis nsample: number of GTEx V6 Esophagus-Muscularis samples
335	FallopianTube minimum: minimum rpkm of GTEx V6 FallopianTube samples
336	FallopianTube maximum: minimum rpkm of GTEx V6 FallopianTube samples
337	FallopianTube average: minimum rpkm of GTEx V6 FallopianTube samples
338	FallopianTube nsample: number of GTEx V6 FallopianTube samples
339	Heart-AtrialAppendage minimum: minimum rpkm of GTEx V6 Heart-AtrialAppendage samples
340	Heart-AtrialAppendage maximum: minimum rpkm of GTEx V6 Heart-AtrialAppendage samples
341	Heart-AtrialAppendage average: minimum rpkm of GTEx V6 Heart-AtrialAppendage samples
342	Heart-AtrialAppendage nsample: number of GTEx V6 Heart-AtrialAppendage samples
343	Heart-LeftVentricle minimum: minimum rpkm of GTEx V6 Heart-LeftVentricle samples
344	Heart-LeftVentricle maximum: minimum rpkm of GTEx V6 Heart-LeftVentricle samples
345	Heart-LeftVentricle average: minimum rpkm of GTEx V6 Heart-LeftVentricle samples
346	Heart-LeftVentricle nsample: number of GTEx V6 Heart-LeftVentricle samples
347	Kidney-Cortex minimum: minimum rpkm of GTEx V6 Kidney-Cortex samples
348	Kidney-Cortex maximum: minimum rpkm of GTEx V6 Kidney-Cortex samples
349	Kidney-Cortex average: minimum rpkm of GTEx V6 Kidney-Cortex samples
350	Kidney-Cortex nsample: number of GTEx V6 Kidney-Cortex samples
351	Liver minimum: minimum rpkm of GTEx V6 Liver samples
352	Liver maximum: minimum rpkm of GTEx V6 Liver samples
353	Liver average: minimum rpkm of GTEx V6 Liver samples
354	Liver nsample: number of GTEx V6 Liver samples
355	Lung minimum: minimum rpkm of GTEx V6 Lung samples
356	Lung maximum: minimum rpkm of GTEx V6 Lung samples
357	Lung average: minimum rpkm of GTEx V6 Lung samples
358	Lung nsample: number of GTEx V6 Lung samples
359	MinorSalivaryGland minimum: minimum rpkm of GTEx V6 MinorSalivaryGland samples
360	MinorSalivaryGland maximum: minimum rpkm of GTEx V6 MinorSalivaryGland samples
361	MinorSalivaryGland average: minimum rpkm of GTEx V6 MinorSalivaryGland samples
362	MinorSalivaryGland nsample: number of GTEx V6 MinorSalivaryGland samples
363	Muscle-Skeletal minimum: minimum rpkm of GTEx V6 Muscle-Skeletal samples
364	Muscle-Skeletal maximum: minimum rpkm of GTEx V6 Muscle-Skeletal samples
365	Muscle-Skeletal average: minimum rpkm of GTEx V6 Muscle-Skeletal samples
366	Muscle-Skeletal nsample: number of GTEx V6 Muscle-Skeletal samples
367	Nerve-Tibial minimum: minimum rpkm of GTEx V6 Nerve-Tibial samples
368	Nerve-Tibial maximum: minimum rpkm of GTEx V6 Nerve-Tibial samples
369	Nerve-Tibial average: minimum rpkm of GTEx V6 Nerve-Tibial samples
370	Nerve-Tibial nsample: number of GTEx V6 Nerve-Tibial samples
371	Ovary minimum: minimum rpkm of GTEx V6 Ovary samples
372	Ovary maximum: minimum rpkm of GTEx V6 Ovary samples
373	Ovary average: minimum rpkm of GTEx V6 Ovary samples
374	Ovary nsample: number of GTEx V6 Ovary samples
375	Pancreas minimum: minimum rpkm of GTEx V6 Pancreas samples
376	Pancreas maximum: minimum rpkm of GTEx V6 Pancreas samples
377	Pancreas average: minimum rpkm of GTEx V6 Pancreas samples
378	Pancreas nsample: number of GTEx V6 Pancreas samples
379	Pituitary minimum: minimum rpkm of GTEx V6 Pituitary samples
380	Pituitary maximum: minimum rpkm of GTEx V6 Pituitary samples
381	Pituitary average: minimum rpkm of GTEx V6 Pituitary samples
382	Pituitary nsample: number of GTEx V6 Pituitary samples
383	Prostate minimum: minimum rpkm of GTEx V6 Prostate samples
384	Prostate maximum: minimum rpkm of GTEx V6 Prostate samples
385	Prostate average: minimum rpkm of GTEx V6 Prostate samples
386	Prostate nsample: number of GTEx V6 Prostate samples
387	Skin-NotSunExposed(Suprapubic) minimum: minimum rpkm of GTEx V6 Skin-NotSunExposed(Suprapubic) samples
388	Skin-NotSunExposed(Suprapubic) maximum: minimum rpkm of GTEx V6 Skin-NotSunExposed(Suprapubic) samples
389	Skin-NotSunExposed(Suprapubic) average: minimum rpkm of GTEx V6 Skin-NotSunExposed(Suprapubic) samples
390	Skin-NotSunExposed(Suprapubic) nsample: number of GTEx V6 Skin-NotSunExposed(Suprapubic) samples
391	Skin-SunExposed(Lowerleg) minimum: minimum rpkm of GTEx V6 Skin-SunExposed(Lowerleg) samples
392	Skin-SunExposed(Lowerleg) maximum: minimum rpkm of GTEx V6 Skin-SunExposed(Lowerleg) samples
393	Skin-SunExposed(Lowerleg) average: minimum rpkm of GTEx V6 Skin-SunExposed(Lowerleg) samples
394	Skin-SunExposed(Lowerleg) nsample: number of GTEx V6 Skin-SunExposed(Lowerleg) samples
395	SmallIntestine-TerminalIleum minimum: minimum rpkm of GTEx V6 SmallIntestine-TerminalIleum samples
396	SmallIntestine-TerminalIleum maximum: minimum rpkm of GTEx V6 SmallIntestine-TerminalIleum samples
397	SmallIntestine-TerminalIleum average: minimum rpkm of GTEx V6 SmallIntestine-TerminalIleum samples
398	SmallIntestine-TerminalIleum nsample: number of GTEx V6 SmallIntestine-TerminalIleum samples
399	Spleen minimum: minimum rpkm of GTEx V6 Spleen samples
400	Spleen maximum: minimum rpkm of GTEx V6 Spleen samples
401	Spleen average: minimum rpkm of GTEx V6 Spleen samples
402	Spleen nsample: number of GTEx V6 Spleen samples
403	Stomach minimum: minimum rpkm of GTEx V6 Stomach samples
404	Stomach maximum: minimum rpkm of GTEx V6 Stomach samples
405	Stomach average: minimum rpkm of GTEx V6 Stomach samples
406	Stomach nsample: number of GTEx V6 Stomach samples
407	Testis minimum: minimum rpkm of GTEx V6 Testis samples
408	Testis maximum: minimum rpkm of GTEx V6 Testis samples
409	Testis average: minimum rpkm of GTEx V6 Testis samples
410	Testis nsample: number of GTEx V6 Testis samples
411	Thyroid minimum: minimum rpkm of GTEx V6 Thyroid samples
412	Thyroid maximum: minimum rpkm of GTEx V6 Thyroid samples
413	Thyroid average: minimum rpkm of GTEx V6 Thyroid samples
414	Thyroid nsample: number of GTEx V6 Thyroid samples
415	Uterus minimum: minimum rpkm of GTEx V6 Uterus samples
416	Uterus maximum: minimum rpkm of GTEx V6 Uterus samples
417	Uterus average: minimum rpkm of GTEx V6 Uterus samples
418	Uterus nsample: number of GTEx V6 Uterus samples
419	Vagina minimum: minimum rpkm of GTEx V6 Vagina samples
420	Vagina maximum: minimum rpkm of GTEx V6 Vagina samples
421	Vagina average: minimum rpkm of GTEx V6 Vagina samples
422	Vagina nsample: number of GTEx V6 Vagina samples
423	WholeBlood minimum: minimum rpkm of GTEx V6 WholeBlood samples
424	WholeBlood maximum: minimum rpkm of GTEx V6 WholeBlood samples
425	WholeBlood average: minimum rpkm of GTEx V6 WholeBlood samples
426	WholeBlood nsample: number of GTEx V6 WholeBlood samples
427	Interactions(IntAct): The number of other genes this gene interacting with (from IntAct).
		Full information (gene name followed by Pubmed id in "[]") can be found in the ".complete"
		table
428	Interactions(BioGRID): The number of other genes this gene interacting with (from BioGRID)
		Full information (gene name followed by Pubmed id in "[]") can be found in the ".complete"
		table
429	Interactions(ConsensusPathDB): The number of other genes this gene interacting with
		(from ConsensusPathDB). Full information (gene name followed by Pubmed id in "[]") can be
		found in the ".complete" table
430	P(HI): Estimated probability of haploinsufficiency of the gene
		(from doi:10.1371/journal.pgen.1001154)
431	P(rec): Estimated probability that gene is a recessive disease gene
		(from DOI:10.1126/science.1215040)
432	Known_rec_info: Known recessive status of the gene (from DOI:10.1126/science.1215040)
		"lof-tolerant = seen in homozygous state in at least one 1000G individual"
		"recessive = known OMIM recessive disease"
		(original annotations from DOI:10.1126/science.1215040)
433	RVIS: Residual Variation Intolerance Score, a measure of intolerance of mutational burden,
		the higher the score the more tolerant to mutational burden the gene is.
		from doi:10.1371/journal.pgen.1003709
434	RVIS_percentile: The percentile rank of the gene based on RVIS, the higher the percentile
		the more tolerant to mutational burden the gene is.
435	RVIS_ExAC_0.05%(AnyPopn): Residual Variation Intolerance Score based on ExAC r0.3 data
436	%RVIS_ExAC_0.05%(AnyPopn): The percentile rank of the gene based on RVIS_ExAC_0.05%(AnyPopn)
437	GDI: gene damage index score, "a genome-wide, gene-level metric of the mutational damage that has
		accumulated in the general population" from doi: 10.1073/pnas.1518646112. The higher the score
		the less likely the gene is to be responsible for monogenic diseases.
438	GDI-Phred: Phred-scaled GDI scores
439	Gene damage prediction (all disease-causing genes): gene damage prediction (low/medium/high) by GDI
		for all diseases
440	Gene damage prediction (all Mendelian disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for all Mendelian diseases
441	Gene damage prediction (Mendelian AD disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for Mendelian autosomal dominant diseases
442	Gene damage prediction (Mendelian AR disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for Mendelian autosomal recessive diseases
443	Gene damage prediction (all PID disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for all primary immunodeficiency diseases
444	Gene damage prediction (PID AD disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for primary immunodeficiency autosomal dominant diseases
445	Gene damage prediction (PID AR disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for primary immunodeficiency autosomal recessive diseases
446	Gene damage prediction (all cancer disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for all cancer disease
447	Gene damage prediction (cancer recessive disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for cancer recessive disease
448	Gene damage prediction (cancer dominant disease-causing genes): gene damage prediction (low/medium/high)
		by GDI for cancer dominant disease
449	LoFtool_score: a percential score for gene intolerance to functional change. The lower the score the higher
		gene intolerance to functional change. For details please contact Dr. Joao Fadista(joao.fadista@med.lu.se)
450	Essential_gene: Essential ("E") or Non-essential phenotype-changing ("N") based on
		Mouse Genome Informatics database. from doi:10.1371/journal.pgen.1003484
451	MGI_mouse_gene: Homolog mouse gene name from MGI
452	MGI_mouse_phenotype: Phenotype description for the homolog mouse gene from MGI
453	ZFIN_zebrafish_gene: Homolog zebrafish gene name from ZFIN
454	ZFIN_zebrafish_structure: Affected structure of the homolog zebrafish gene from ZFIN
455	ZFIN_zebrafish_phenotype_quality: Phenotype description for the homolog zebrafish gene
		from ZFIN
456	ZFIN_zebrafish_phenotype_tag: Phenotype tag for the homolog zebrafish gene from ZFIN
"""