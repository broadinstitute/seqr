

class Datastore(object):
    """

    A Datastore stores variant calls. This abstract class just provides a basic set of variant access methods -
    it's meant to be backend-agnostic. The canonical datastore implementation, MongoDatastore, uses MongoDB,
    but we plan to develop

    Samples are identified by (project_id, indiv_id) - both strings.
    This is meant to be flexible - can use different project IDs to test different versions of a calling algorithm,
    but on the same underlying samples

    Samples are organized in "families", which should really be named "sample sets".

    Random notes:
    - I'm not sure whether this will become "VariantDatastore",
    which only stores variant calls, or "Datastore", which stores all other variant call-related info,
    eg. raw reads, coverage, etc.

    - Decided to use protocol for datastore instead of ABC because some
    datastores might not implement all methods.
    Also, I'm still kind of awkward with ABCs, as the above comment probably shows

    - Not sure if Datastore should explicitly require an annotator, or if not how we should support generic annotator

    - Note that right now datastore doesn't consider quality filters, though it probably should

    """

    #
    #
    # Variant lookup methods
    #
    #

    def get_variants(self, project_id, family_id, genotype_filter=None, variant_filter=None, quality_filter=None, indivs_to_consider=None, user=None):
        """
        Get variants with a specific genotype *combination* in a family
        No error checking, assumes that caller knows what she is doing
        Returns variant iterator
        """
        raise NotImplementedError

    def get_variants_in_gene(self, project_id, family_id, gene_id, genotype_filter=None, variant_filter=None, quality_filter=None, indivs_to_consider=None):
        """
        Same as get_variants, but restrict to a given gene_id
        Note that gene_id kinda clashes with variant_filter, which has a `genes` attribute
        This *appends* gene_id to the variant filter genes, so you can actually combine them.
        If variant_filter.genes is ['GENE1',] and gene_id is 'GENE2', will return variants in *both* genes
        That said, you probably don't want to do this.
        """
        raise NotImplementedError

    def get_single_variant(self, project_id, family_id, xpos, ref, alt, user=None):
        """
        Get a single variant in a family
        Variant should be identifiable by xpos, ref, and alt
        Note that ref and alt are just strings from the VCF (for now)
        """
        raise NotImplementedError

    def get_multiple_variants(self, project_id, family_id, xpos_ref_alt_tuples, user=None):
        """
        Get one or more specific variants in a family
        Variant should be identifiable by xpos, ref, and alt
        Note that ref and alt are just strings from the VCF (for now)
        """
        for xpos, ref, alt in xpos_ref_alt_tuples:
            yield self.get_single_variant(project_id, family_id, xpos, ref, alt, user=None)

    def get_variants_cohort(self, project_id, cohort_id, variant_filter=None):
        """
        Same as get_variants above, returning cohort variants
        However, note that there is nothing analogous to genotype_filter here -
        you will always get all variants where anybody in the cohort has an alt allele

        TODO: we should add a cohort_genotype_filter args so you can specify, eg. at least two indivs are alt/alt
        """
        raise NotImplementedError

    def get_single_variant_cohort(self, project_id, cohort_id, xpos, ref, alt):
        """
        Same as get_single_variant, but for cohorts
        """
        raise NotImplementedError

    def get_snp_array(self, project_id, family_id, indiv_id):
        """
        Gets exome-wide SNP array for this individual
        This is probably poorly named - here snp_array is just an array of
        common SNPs in the exome, the actual locations determined by settings.COMMON_SNP_FILE
        """
        raise NotImplementedError

    def get_family_stats(self, project_id, family_id):
        """
        Variant statistics for a family...
        {
            annot_counts: ...
            group_annot_counts: ...
        }
        """
        raise NotImplementedError

    def bust_project_cache(self, project_id):
        if hasattr(self, '_redis_client') and self._redis_client:
            for key in self._redis_client.scan_iter("Variants___{}*".format(project_id)):
                self._redis_client.delete(key)
