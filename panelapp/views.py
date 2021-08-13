from seqr.utils.logging_utils import SeqrLogger
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import superuser_required

logger = SeqrLogger(__name__)


@superuser_required
def import_panelapp_handler(request):
    return create_json_response({})
