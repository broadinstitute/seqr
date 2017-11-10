import collections
import os
import settings
import sys

from xbrowse.core.genomeloc import get_xpos


# maps (xpos, ref, alt) to a 2-tuple containing (variation_id, clinical_significance)
_CLINVAR_VARIANTS = None


def get_clinvar_variants():
    global _CLINVAR_VARIANTS

    if _CLINVAR_VARIANTS is None:
        if not settings.CLINVAR_TSV:
            raise ValueError("settings.CLINVAR_TSV not set")

        if not os.path.isfile(settings.CLINVAR_TSV):
            raise ValueError("settings.CLINVAR_TSV file not found: %s" % (settings.CLINVAR_TSV,))

        _CLINVAR_VARIANTS = {}

        header = None
        pathogenicity_values_counter = collections.defaultdict(int)

        #print("Reading Clinvar data into memory: " + CLINVAR_TSV)
        for line in open(settings.CLINVAR_TSV):
            line = line.strip()
            if line.startswith("#"):
                continue
            fields = line.split("\t")
            if header is None:
                header = fields
                if "clinical_significance" not in line.lower():
                    raise ValueError("'clinical_significance' not found in header line: %s" % str(header))
                continue

            try:
                if "clinical_significance" in line.lower():
                    raise ValueError("'clinical_significance' found in non-header line: %s" % str(header))

                line_dict = dict(zip(header, fields))
                chrom = line_dict["chrom"]
                pos = int(line_dict["pos"])
                ref = line_dict["ref"]
                alt = line_dict["alt"]
                if "M" in chrom:
                    continue   # because get_xpos doesn't support chrMT.
                clinical_significance = line_dict["clinical_significance"].lower()
                if clinical_significance in ["not provided", "other", "association"]:
                    continue
                else:
                    for c in clinical_significance.split(";"):
                        pathogenicity_values_counter[c] += 1
                    xpos = get_xpos(chrom, pos)

                    _CLINVAR_VARIANTS[(xpos, ref, alt)] = (line_dict["variation_id"], clinical_significance)

                    #for k in sorted(pathogenicity_values_counter.keys(), key=lambda k: -pathogenicity_values_counter[k]):
                    #    sys.stderr.write(("     %5d  %s\n"  % (pathogenicity_values_counter[k], k)))
                    #sys.stderr.write("%d clinvar variants loaded \n" % len(CLINVAR_VARIANTS))

            except Exception as e:
                sys.stderr.write("Error while parsing clinvar row: \n%s\n %s\n" % (line, e,))

    return _CLINVAR_VARIANTS