class PopulationVariationStore():
    """

    """

    def get_populations(self):
        """
        List of populations (slugs)
        """
        raise NotImplementedError

    def get_population_variation(self, xpos, ref, alt):
        """
        Get population variation for this variant
        Is just a dict of { slug: float },
        May not have all populations - entry with value of 0.0 implies that variant affirmatively was not seen
        """
        raise NotImplementedError