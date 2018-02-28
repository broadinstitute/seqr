import gzip
import settings
import tqdm
from xbrowse.core.genomeloc import get_xpos


def parse_clinvar_tsv(clinvar_tsv_path=None):
    """Load clinvar tsv file

    Args:
        clinvar_tsv_path (string): optional alternate path
    """
    if clinvar_tsv_path is None:
        clinvar_tsv_path = settings.REFERENCE_SETTINGS.clinvar_tsv_file

    header = None

    clinvar_file = gzip.open(clinvar_tsv_path) if clinvar_tsv_path.endswith(".gz") else open(clinvar_tsv_path)
    for line in tqdm.tqdm(clinvar_file, unit=" clinvar records"):
        line = line.strip()
        if line.startswith("#"):
            continue

        fields = line.split("\t")
        if header is None:
            if "clinical_significance" not in line.lower():
                raise ValueError("'clinical_significance' not found in header line: %s" % str(header))
            header = fields
            continue
        else:
            if "clinical_significance" in line.lower():
                raise ValueError("'clinical_significance' found in non-header line: %s" % str(header))

        fields = dict(zip(header, fields))
        chrom = fields["chrom"]
        pos = int(fields["pos"])
        ref = fields["ref"]
        alt = fields["alt"]
        if "M" in chrom:
            continue   # because get_xpos doesn't support chrMT.

        clinical_significance = fields["clinical_significance"].lower()
        if clinical_significance in ["not provided", "other", "association"]:
            continue

        yield {
            'xpos': get_xpos(chrom, pos),
            'ref': ref,
            'alt': alt,
            'variant_id': fields.get("variation_id") or fields.get("measureset_id"),
            'clinsig': clinical_significance,
        }