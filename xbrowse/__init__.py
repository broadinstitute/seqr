from .core.samples import Individual, Family, Cohort, FamilyGroup

from .core.variants import Variant, Genotype

from .core.genomeloc import get_xpos

# TODO: remove everything below this line - just here for back compatibility
from .core import genomeloc
from .core import constants
from .core import variant_filters
from .core import quality_filters
from .core import genotype_filters
from .core import family_utils
from .core import inheritance
from .core import inheritance_modes
from .core import samples
from .core import stream_utils

from .parsers import vcf_stuff
from .parsers import fam_stuff