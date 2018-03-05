import gzip
import settings
import tqdm
from xbrowse.core.genomeloc import get_xpos
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
        _parse_clinvar_info(fields)
        chrom = fields["CHROM"]
        pos = int(fields["POS"])
        ref = fields["REF"]
        alt = fields["ALT"]
        if "M" in chrom or "N" in chrom:
            continue   # because get_xpos doesn't support chrMT or chrNW.

        clinical_significance = fields.get("CLNSIG", "").lower()
        if clinical_significance in ["", "not provided", "other", "association"]:
            continue

        yield {
            'xpos': get_xpos(chrom, pos),
            'ref': ref,
            'alt': alt,
            'variant_id': fields["ID"],
            'clinsig': clinical_significance,
        }


def _parse_clinvar_info(clinvar_fields):
    info_fields = dict([info.split('=') for info in clinvar_fields['INFO'].split(';')])
    clinvar_fields.update(info_fields)
