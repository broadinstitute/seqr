from panelapp.panelapp_utils import import_all_panels
from seqr.utils.logging_utils import SeqrLogger
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import data_manager_required

logger = SeqrLogger(__name__)


@data_manager_required
def import_panelapp_handler(request):
    import_all_panels(request.user)

    return create_json_response({})
