
def add_annotation_index_to_variant(variant, annotator):
    """
    Datastore doesn't need to know the whole annotation for a variant,
    so this method just attaches relevant annotation fields. They are:

    - vartype
    - effects.vep
    - freqs
    - polyphen
    - gene_ids
    - single_position
    - single_position_end
    - posindex

    ** For now, this adds full annotation to the variant. This is a temporary stopgap **
    * These are going to change frequently in the next month *

    """
    pass