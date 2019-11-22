import gzip
import settings
import tqdm
from xbrowse.core.genomeloc import get_xpos, valid_chrom
from xbrowse.parsers.vcf_stuff import get_vcf_headers


def parse_clinvar_vcf(clinvar_vcf_path=None):
    """Load clinvar vcf file

    Rows have the following format:

    #CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
    1\t949422\t475283\tG\tA\t.\t.\tALLELEID=446939;CLNDISDB=MedGen:C4015293,OMIM:616126,Orphanet:ORPHA319563;CLNDN=Immunodeficiency_38_with_basal_ganglia_calcification;CLNHGVS=NC_000001.10:g.949422G>A;CLNREVSTAT=criteria_provided,_single_submitter;CLNSIG=Benign;CLNVC=single_nucleotide_variant;CLNVCSO=SO:0001483;GENEINFO=ISG15:9636;MC=SO:0001583|missense_variant;ORIGIN=1;RS=143888043

    Args:
        clinvar_vcf_path (string): optional alternate path
    """
    if clinvar_vcf_path is None:
        clinvar_vcf_path = settings.REFERENCE_SETTINGS.clinvar_vcf_file

    header = None

    clinvar_file = gzip.open(clinvar_vcf_path) if clinvar_vcf_path.endswith(".gz") else open(clinvar_vcf_path)

    for line in tqdm.tqdm(clinvar_file, unit=" clinvar records"):
        line = line.strip()
        if line.startswith("##"):
            continue

        if header is None:
            header = get_vcf_headers(line)
            continue

        fields = line.split("\t")
        fields = dict(zip(header, fields))
        info_fields = dict([info.split('=') for info in fields['INFO'].split(';')])
        fields.update(info_fields)
        chrom = fields["CHROM"]
        pos = int(fields["POS"])
        ref = fields["REF"]
        alt = fields["ALT"]
        variant_id = fields["ID"]

        if not valid_chrom(chrom):
            continue

        clinical_significance = fields.get("CLNSIG", "").lower()
        if clinical_significance in ["", "not provided", "other", "association"]:
            continue

        yield {
            'xpos': get_xpos(chrom, pos),
            'ref': ref,
            'alt': alt,
            'variant_id': variant_id,
            'clinsig': clinical_significance,
        }
