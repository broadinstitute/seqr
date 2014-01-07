
def get_tissue_expression_values_by_gene(expression_file_name, samples_file_name):
    """
    Return iterator of (gene_id, expression array) tuples
    Expression array is:
    expressions: {
        tissue_type: [array of expression values]
    }

    expression_file (RPKM_GeneLevel_September.gct) is in gtex format; 
    samples file is just two columns: sample -> tissue type

    Command for getting samples file:
    awk -F"\t" '{ gsub(/ /,"_",$47); gsub(/-/,".",$1); print $1"\t"tolower($47) }' RNA-SeQC_metrics_September.tsv > gtex_samples.txt

    """

    # read samples file to get a map of sample_id -> tissue_type
    tissue_type_map = get_tissue_type_map(samples_file_name)

    expression_file = open(expression_file_name)

    for i, line in enumerate(expression_file):
        line = line.strip('\n')
        if i % 1000 == 0:
            print i

        if not line:
            break

        # first two lines are junk; third is the header
        if i < 2:
            continue
        if i == 2:
            # read header of expression file to get tissue type list
            # (used to link column to tissue type)
            # this wouldn't be necessary if samples file is in the same order as expression file,
            # but I don't wait to rely on that guarantee (mainly because they have a different # of fields)
            tissues_by_column = get_tissues_by_column(line, tissue_type_map)
            continue

        fields = line.split('\t')
        gene_id = fields[0].split('.')[0]

        yield (gene_id, get_expressions(line, tissues_by_column))


def get_tissue_type_map(samples_file): 
    """
    Returns map of sample id -> tissue type
    """
    tissue_type_map = {}
    f = open(samples_file)
    for i, line in enumerate(open(samples_file).read().splitlines()):

        if i == 0: continue # skip header line
        fields = line.split('\t')
        tissue_type_map[fields[0]] = fields[1]

    return tissue_type_map

def get_tissues_by_column(header_line, tissue_type_map):
    """
    Return a list of tissue types for each sample in header
    (len is # fields - 2, as first two fields ID the gene)
    type is None if a sample is not in tissue_type_map
    """
    header_fields = header_line.strip().split('\t')
    num_samples = len(header_fields) - 2
    tissue_types = [ None for i in range(num_samples) ]
    for i in range(num_samples): 
        tissue_types[i] = tissue_type_map.get(header_fields[i+2])
    return tissue_types


def get_expressions(line, tissues_by_column): 
    """
    Make an expression map from a data line in the expression file
    """
    uniq_expressions = set(tissues_by_column)
    expressions = {e: [] for e in uniq_expressions if e is not None and e != 'na' }

    fields = line.strip().split('\t')
    for i in range(len(fields)-2): 
        tissue = tissues_by_column[i]
        if expressions.has_key(tissue): 
            expressions[tissue].append(float(fields[i+2]))
    return expressions


