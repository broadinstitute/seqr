#!/usr/bin/env python

__author__ = 'konradjk'

import argparse
import gzip
import re
import sys
from loftee_utils import *
import copy
import pipes
import subprocess
import time
try:
    from minimal_representation import get_minimal_representation
except ImportError, e:
    get_minimal_representation = None
    print >> sys.stderr, "WARNING: Did not find minimal_representation. Outputting raw positions."


def main(args):
    bgzip = False
    try:
        subprocess.check_output(["tabix"], stderr=subprocess.STDOUT)
    except OSError, e:
        pass
    except Exception, e:
        bgzip = True
    print >> sys.stderr, "SUCCESS: Found bgzip! Will bgzip the table." if bgzip else "WARNING: Could not find bgzip. Proceeding without..."

    # Read parameters
    f = gzip.open(args.vcf) if args.vcf.endswith('.gz') else open(args.vcf)
    if args.output is None:
        args.output = '.table'.join(args.vcf.rsplit('.vcf', 1))
    if args.output == args.vcf:
        print >> sys.stderr, "VCF filename has no '.vcf' and no output file name was provided. Exiting."
        sys.exit(1)
    if args.split_size is not None:
        if '.table.gz' not in args.output: print >> sys.stderr, "Output filename has no '.table.gz' extension. Adding and proceeding..."
        args.output = args.output.rsplit('.table.gz', 1)[0] + '_%04d.table.gz'
        output_file = args.output % 0
    else:
        output_file = args.output
    if not args.options:
        if bgzip:
            pipe = pipes.Template()
            pipe.append('bgzip -c /dev/stdin', '--')
        else:
            pipe = gzip
        g = pipe.open(output_file, 'w') if output_file.endswith('.gz') else open(output_file, 'w')

    desired_info = [] if args.info is None else args.info.split(',')
    desired_vep_info = [] if args.vep_info is None else args.vep_info.split(',')
    desired_sample_info = [] if args.sample_info is None else args.sample_info.split(',')

    missing_string = '\N' if args.mysql else 'NA'

    header = None
    vep_field_names = None
    info_from_header = {}
    started = False
    last_chr = ''

    log = open(output_file + '.log', 'w')
    print >> log, 'Running file: %s' % args.vcf
    print >> log, 'Started at: %s' % time.strftime("%Y_%m_%d_%H_%M_%S")
    print >> log, '\n'.join(['--%s %s' % (k, v) for k, v in args.__dict__.iteritems()])
    log.close()

    output_header = 'CHROM\tPOS\tREF\tALT'
    if args.add_ucsc_link: output_header += '\tUCSC'
    if args.include_id: output_header += '\tID'
    if args.original_position: output_header += '\tORIGINAL_POSITION'
    if not args.omit_filter: output_header += '\tFILTER'

    raw_ucsc_link = 'http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg19&position=chr%s:%s-%s'

    num_lines = 0
    file_no = 0
    for line in f:
        try:
            line = line.strip()

            # Reading header lines to get VEP and individual arrays
            if line.startswith('#'):
                line = line.lstrip('#')
                if line.startswith('INFO=<ID='):
                    try:
                        header_metadata = dict([x.split('=', 1) for x in line.split('<')[1].split('>')[0].split(',', 3) if '=' in x])
                    except Exception, e:
                        print >> sys.stderr, "Malformed header line: %s" % line
                        sys.exit(1)
                    info_from_header[header_metadata['ID']] = header_metadata
                if 'ID=CSQ' in line:
                    vep_field_names = line.split('Format: ')[-1].strip('">').split('|')
                    vep_info_from_header = dict(zip(vep_field_names, range(len(vep_field_names))))
                if line.startswith('CHROM'):
                    header_list = line.split('\t')
                    header = dict(zip(header_list, range(len(header_list))))
                    if args.options:
                        print >> sys.stderr, "######### OPTIONS FOR INFO #########"
                        for info in info_from_header:
                            print >> sys.stderr, '%s\t%s' % (info, info_from_header[info]['Description'])
                        if vep_field_names is not None:
                            print >> sys.stderr, "######### OPTIONS FOR VEP_INFO #########"
                            print >> sys.stderr, '\n'.join(vep_field_names)
                        sys.exit(0)
                continue

            if len(desired_vep_info) > 0:
                if vep_field_names is None:
                    print >> sys.stderr, "VEP info requested, but VCF file does not have a VEP header line. Exiting."
                    sys.exit(1)
                if 'ALLELE_NUM' not in vep_info_from_header:
                    print >> sys.stderr, "VEP output does not have ALLELE_NUM which is required for extraction. Please re-run VEP with --allele_number. Exiting."
                    sys.exit(1)

            if header is None:
                print >> sys.stderr, "VCF file does not have a header line (CHROM POS etc.). Exiting."
                sys.exit(1)

            if not started:
                # Allowing entries even if not found in the header line, with some caveats
                original_desired_info = copy.deepcopy(desired_info)
                desired_info = []
                any_missing = 0
                for info in original_desired_info:
                    if info in info_from_header:
                        print >> sys.stderr, 'SUCCESS: Found %s: %s' % (info, info_from_header[info]['Description'])
                        desired_info.append(info)
                    else:
                        matches = 0
                        for header_record in info_from_header:
                            if re.search('^%s$' % info, header_record):
                                matches += 1
                                desired_info.append(header_record)
                                print >> sys.stderr, 'SUCCESS: Found %s (matching %s): %s' % (header_record, info, info_from_header[header_record]['Description'])
                        if not matches:
                            print >> sys.stderr, 'WARNING: Did not find %s in header.' % info
                            any_missing += 1
                            desired_info.append(info)

                # Only allowing entries in VEP header.
                original_desired_vep_info = copy.deepcopy(desired_vep_info)
                desired_vep_info = []
                for info in original_desired_vep_info:
                    if info in vep_info_from_header:
                        desired_vep_info.append(info)
                        print >> sys.stderr, 'SUCCESS: Found %s' % info
                    else:
                        matches = 0
                        for header_record in vep_info_from_header:
                            if re.search('^%s$' % info, header_record):
                                matches += 1
                                desired_vep_info.append(header_record)
                                print >> sys.stderr, 'SUCCESS: Found %s (matching %s)' % (header_record, info)
                        if not matches:
                            print >> sys.stderr, 'WARNING: Did not find %s in VEP header. Not including from here on out.' % info
                            any_missing += 1

                # Getting info from individuals
                original_desired_sample_info = copy.deepcopy(desired_sample_info)
                desired_sample_info = []
                if len(original_desired_sample_info) > 0:
                    if 'FORMAT' not in header:
                        print >> sys.stderr, 'WARNING: Did not find FORMAT in header line, will not be extracting any SAMPLE.FORMATs'
                    else:
                        for info in original_desired_sample_info:
                            sample_format = info.split('.')
                            if len(sample_format) != 2:
                                print >> sys.stderr, 'WARNING: %s is not a SAMPLE.FORMAT designation' % sample_format
                            else:
                                sample, format = sample_format
                                if sample in header:
                                    print >> sys.stderr, 'SUCCESS: Found sample %s in header' % sample
                                    desired_sample_info.append(info)
                                else:
                                    print >> sys.stderr, 'WARNING: Sample %s not found in header' % sample

                # Warnings/errors for missing data
                if any_missing: print >> sys.stderr, 'WARNING: At least one INFO line requested was not found. Continuing, but results may be off.'
                if len(desired_info) + len(desired_vep_info) + len(desired_sample_info) == 0:
                    print >> sys.stderr, 'No fields left in requested info/VEP info. Exiting.'
                    sys.exit(1)
                if args.lof_only and 'LoF' not in desired_vep_info:
                    print >> sys.stderr, '--lof_only was used, but no LoF tag found in VEP field. Exiting.'
                    sys.exit(1)

                # Ready to go.
                if len(desired_info) > 0: output_header += '\t' + '\t'.join(desired_info)
                if len(desired_sample_info) > 0: output_header += '\t' + '\t'.join(desired_sample_info)
                if args.samples: output_header += '\tSAMPLES'
                if args.hom_samples: output_header += '\tHOM_SAMPLES'
                if len(desired_vep_info) > 0: output_header += '\t' + '\t'.join(desired_vep_info)
                print >> g, output_header
                started = True

            # Pull out annotation info from INFO and ALT fields
            fields = line.split('\t')
            info_field = dict([(x.split('=', 1)) if '=' in x else (x, x) for x in re.split(';(?=\w)', fields[header['INFO']].replace('"', ''))])

            if args.only_pass and fields[header['FILTER']] != 'PASS': continue
            alts = fields[header['ALT']].split(',')
            if args.biallelic_only and len(alts) > 1: continue

            # Only get VEP info if requested
            if len(desired_vep_info) > 0:
                if 'CSQ' in info_field:
                    # if statement in list comp below is a fix for VEP's occasional introduction of a semi-colon into the CSQ.
                    # Can be removed once that is completely fixed.
                    annotations = [dict(zip(vep_field_names, x.split('|'))) for x in info_field['CSQ'].split(',') if len(vep_field_names) == len(x.split('|'))]
                    if args.lof_only: annotations = [x for x in annotations if x['LoF'] == 'HC']
                    if args.canonical_only: annotations = [x for x in annotations if x['CANONICAL'] == 'YES']
                else:
                    annotations = []
                if args.lof_only and len(annotations) == 0: continue
                if args.canonical_only and len(annotations) == 0: continue

            if 'FORMAT' in header:
                format_fields_list = fields[header['FORMAT']].split(':')
                format_fields = dict(zip(format_fields_list, range(len(format_fields_list))))

            for index, alt in enumerate(alts):
                # Get site data
                if not args.do_not_minrep and get_minimal_representation is not None:
                    new_pos, new_ref, new_alt = get_minimal_representation(fields[header['POS']], fields[header['REF']], alt)
                    if args.snps_only and (len(new_ref) != 1 or len(new_alt) != 1): continue
                    output = [fields[header['CHROM']], str(new_pos), new_ref, new_alt]
                else:
                    if args.snps_only and (len(fields[header['REF']]) != 1 or len(alt) != 1): continue
                    output = [fields[header['CHROM']], fields[header['POS']], fields[header['REF']], alt]

                ucsc_link = raw_ucsc_link % (output[0], int(output[1]) - args.ucsc_link_window, int(output[1]) + args.ucsc_link_window)
                if args.add_ucsc_link: output.append(ucsc_link)
                if args.include_id: output.append(fields[header['ID']])
                if args.original_position: output.append(fields[header['POS']])
                if not args.omit_filter: output.append(fields[header['FILTER']])

                # Get data from INFO field
                for info in desired_info:
                    this_output = missing_string
                    if info in info_field:
                        this_output = info_field[info]
                        if info in info_from_header and 'Number' in info_from_header[info]:
                            if info_from_header[info]['Number'] == 'A':
                                this_output = info_field[info].split(',')[index]
                            elif info_from_header[info]['Number'] == 'R':
                                this_output = info_field[info].split(',')[index + 1]
                            elif info_from_header[info]['Number'] == '0':
                                this_output = info
                    if this_output == '' or this_output == '.': this_output = missing_string
                    output.append(this_output)

                # Get data out of samples (genotype fields)
                for sample_format in desired_sample_info:
                    sample, format = sample_format.split('.')
                    if format not in format_fields: continue
                    this_sample_format = dict(zip(format_fields_list, fields[header[sample]].split(':')))
                    if format in this_sample_format:
                        output.append(this_sample_format[format])
                    else:
                        output.append(missing_string)

                if args.samples:
                    output.append(','.join([header_list[i + 9] for i, x in enumerate(fields[9:]) if str(index + 1) in x.split(':')[0].split('/')]))

                if args.hom_samples:
                    output.append(','.join([header_list[i + 9] for i, x in enumerate(fields[9:]) if all([str(index + 1) == y for y in x.split(':')[0].split('/')])]))

                # Get data out of VEP field
                if len(desired_vep_info) > 0:
                    # Filter to this allele
                    this_alt_annotations = [x for x in annotations if int(x['ALLELE_NUM']) - 1 == index]
                    if args.lof_only and len(this_alt_annotations) == 0: continue
                    if args.canonical_only and len(this_alt_annotations) == 0: continue

                    if args.split_by_transcript:
                        for this_alt_transcript_annotation in this_alt_annotations:
                            new_output = copy.deepcopy(output)
                            for info in desired_vep_info:
                                this_alt_vep_info = this_alt_transcript_annotation[info]

                                # Process options
                                if not args.all_csqs and info == 'Consequence': this_alt_vep_info = worst_csq_from_csq(this_alt_vep_info)
                                if args.simplify_gtex and info == 'TissueExpression':
                                    # Converting from tissue1:value1&tissue2:value2 to [tissue1, tissue2]
                                    this_alt_vep_info = set([y.split(':')[0] for y in this_alt_vep_info.split('&')])
                                    this_alt_vep_info = ','.join(this_alt_vep_info)

                                if this_alt_vep_info == '' or this_alt_vep_info == '.': this_alt_vep_info = missing_string
                                new_output.append(this_alt_vep_info)
                            print >> g, '\t'.join(new_output)
                            num_lines += 1
                    elif args.split_by_gene:
                        for gene in get_set_from_annotation(this_alt_annotations, 'Gene'):
                            # Pre-filtering to worst annotations for this gene
                            this_alt_gene_annotations = worst_csq_with_vep_all(filter_annotation(this_alt_annotations, 'Gene', gene))
                            try:
                                if any([x['LoF'] == 'HC' for x in this_alt_gene_annotations]):
                                    this_alt_gene_annotations = filter_annotation(this_alt_gene_annotations, 'LoF')
                                elif any([x['LoF'] == 'LC' for x in this_alt_gene_annotations]):
                                    this_alt_gene_annotations = filter_annotation(this_alt_gene_annotations, 'LoF', 'LC')
                            except KeyError:
                                pass
                            new_output = copy.deepcopy(output)
                            for info in desired_vep_info:
                                this_alt_vep_info = [x[info] for x in this_alt_gene_annotations if x[info] != '']

                                # Process options
                                if not args.all_csqs and info == 'Consequence': this_alt_vep_info = [worst_csq_from_csq(x) for x in this_alt_vep_info]
                                if args.simplify_gtex and info == 'TissueExpression':
                                    # Converting from tissue1:value1&tissue2:value2 to [tissue1, tissue2]
                                    this_alt_vep_info = set([y.split(':')[0] for x in this_alt_vep_info for y in x.split('&')])
                                if not args.dont_collapse_annotations:
                                    this_alt_vep_info = set(this_alt_vep_info)
                                    # Collapse consequence further
                                    if not args.all_csqs and info == 'Consequence': this_alt_vep_info = [worst_csq_from_list(this_alt_vep_info)]
                                    if args.functional_simplify and len(this_alt_vep_info) > 0 and info in ['PolyPhen', 'SIFT']:
                                        simplified = simplify_polyphen_sift(this_alt_vep_info, info)
                                        if simplified is not None:
                                            this_alt_vep_info = ["%s(%s)" % simplified]

                                annotation_output = ','.join(this_alt_vep_info)
                                if annotation_output == '' or annotation_output == '.': annotation_output = missing_string
                                new_output.append(annotation_output)
                            print >> g, '\t'.join(new_output)
                            num_lines += 1
                    else:
                        # Pre-filtering to worst annotations
                        this_alt_annotations = worst_csq_with_vep_all(this_alt_annotations)
                        try:
                            if any([x['LoF'] == 'HC' for x in this_alt_annotations]):
                                this_alt_annotations = filter_annotation(this_alt_annotations, 'LoF')
                            elif any([x['LoF'] == 'LC' for x in this_alt_annotations]):
                                this_alt_annotations = filter_annotation(this_alt_annotations, 'LoF', 'LC')
                        except KeyError:
                            pass
                        for info in desired_vep_info:
                            this_alt_vep_info = [x[info] for x in this_alt_annotations if x[info] != '']

                            # Process options
                            if not args.all_csqs and info == 'Consequence': this_alt_vep_info = [worst_csq_from_csq(x) for x in this_alt_vep_info]
                            if args.simplify_gtex and info == 'TissueExpression':
                                # Converting from tissue1:value1&tissue2:value2 to [tissue1, tissue2]
                                this_alt_vep_info = set([y.split(':')[0] for x in this_alt_vep_info for y in x.split('&')])
                            if not args.dont_collapse_annotations:
                                this_alt_vep_info = set(this_alt_vep_info)
                                # Collapse consequence further
                                if not args.all_csqs and info == 'Consequence': this_alt_vep_info = [worst_csq_from_list(this_alt_vep_info)]
                                if args.functional_simplify and len(this_alt_vep_info) > 0 and info in ['PolyPhen', 'SIFT']:
                                    simplified = simplify_polyphen_sift(this_alt_vep_info, info)
                                    if simplified is not None:
                                        this_alt_vep_info = ["%s(%s)" % simplified]

                            annotation_output = ','.join(this_alt_vep_info)
                            if annotation_output == '' or annotation_output == '.': annotation_output = missing_string
                            output.append(annotation_output)
                        print >> g, '\t'.join(output)
                        num_lines += 1
                else:
                    print >> g, '\t'.join(output)
                    num_lines += 1
                chrom = fields[header['CHROM']]
                if args.split_size is not None and args.split_size <= num_lines:
                    file_no += 1
                    num_lines = 0
                    g.close()
                    output_file = args.output % file_no
                    g = pipe.open(output_file, 'w') if output_file.endswith('.gz') else open(output_file, 'w')
                    print >> g, output_header

                if chrom != last_chr:
                    last_chr = chrom
                    print >> sys.stderr, "%s." % chrom,
        except Exception, e:
            import traceback
            traceback.print_exc()
            print >> sys.stderr, "FAILED ON LINE: %s" % line
            raise e
    print >> sys.stderr
    f.close()
    g.close()
    if args.split_size is None and bgzip and args.output.endswith('.gz'):
        try:
            subprocess.check_output(['tabix', '-p', 'vcf', args.output])
        except Exception, e:
            print >> sys.stderr, "WARNING: Tabix of table failed - perhaps original VCF was out of order, or minrepping put this out of order."
    print >> sys.stderr, "Done!"

if __name__ == '__main__':
    INFO = '''Parses VCF to extract data from INFO field, VEP annotation (CSQ from inside INFO field), or sample info.
By default, splits VCF record into one allele per line and creates R/MySQL/etc readable table.
For VEP info extraction, VEP must be run with --allele_number.'''
    parser = argparse.ArgumentParser(description=INFO)

    parser.add_argument('--vcf', '--input', '-i', help='Input VCF file; may be gzipped', required=True)
    parser.add_argument('--output', '-o', help='Output table file (default=input{-.vcf}.table[.gz]); may be gzipped')
    parser.add_argument('--options', action='store_true', help='Print possible info and vep_info options (from header) and exit')

    include_arguments = parser.add_argument_group('Fields to include', '(at least one of info, vep_info, or sample_info is required)')
    include_arguments.add_argument('--omit_filter', action='store_true', help='Omit FILTER field from output')
    include_arguments.add_argument('--include_id', action='store_true', help='Include ID field in output')
    include_arguments.add_argument('--original_position', action='store_true', help='Include original position (pre-minrep)')
    include_arguments.add_argument('--add_ucsc_link', action='store_true', help='Writes link to UCSC for this variant (see ucsc_link_window)')
    include_arguments.add_argument('--info', help='Comma separated list of INFO fields to extract (regex allowed)')
    include_arguments.add_argument('--vep_info', help='Comma separated list of CSQ sub-fields to extract (regex allowed)')
    include_arguments.add_argument('--sample_info', help='Comma separated list of SAMPLE.FORMAT to extract')
    include_arguments.add_argument('--samples', help='Get list of variants with each particular allele', action='store_true')
    include_arguments.add_argument('--hom_samples', help='Get list of variants with each particular allele (hom)', action='store_true')

    annotation_arguments = parser.add_argument_group('Annotation arguments')
    annotation_arguments.add_argument('--lof_only', action='store_true', help='Limit output to HC LoF')
    annotation_arguments.add_argument('--canonical_only', action='store_true', help='Limit output to variants in the canonical transcript')
    annotation_arguments.add_argument('--simplify_gtex', action='store_true', help='Simplify GTEx info (only print expressed tissues, not expression values)')
    annotation_arguments.add_argument('--split_by_transcript', help='Split file further into one line per transcript-allele pair', action='store_true')
    annotation_arguments.add_argument('--split_by_gene', help='Split file further into one line per gene-allele pair', action='store_true')
    annotation_arguments.add_argument('--dont_collapse_annotations', action='store_true', help='Do not collapse identical annotations')
    annotation_arguments.add_argument('--all_csqs', action='store_true', help='Print all consequences for each annotation (not just max)')
    annotation_arguments.add_argument('--functional_simplify', action='store_true', help='Simplify PolyPhen/SIFT down to most severe')

    output_options = parser.add_argument_group('Output options')
    output_options.add_argument('--split_size', '-s', help='Split into chunks of this size', type=int, nargs='?', const=1, default=None)
    output_options.add_argument('--mysql', action='store_true', help='Uses \N for missing data for easy reading into MySQL (default = NA, for R)')
    output_options.add_argument('--only_pass', help='Only consider PASS variants', action='store_true')
    output_options.add_argument('--snps_only', help='Only output SNPs', action='store_true')
    output_options.add_argument('--biallelic_only', help='Only consider biallelic variants', action='store_true')
    output_options.add_argument('--ucsc_link_window', help='Window size for UCSC link', type=int, default=20)
    output_options.add_argument('--do_not_minrep', help='Skip minimal representation', action='store_true')

    args = parser.parse_args()
    main(args)