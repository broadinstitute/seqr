from django.contrib.auth.decorators import login_required
from seqr.views.utils.json_utils import render_with_initial_json
from seqr.views.utils.orm_to_json_utils import _get_json_for_user


@login_required
def main_app(request):
    """Loads the react single page app."""

    return render_with_initial_json('app.html', {'user': _get_json_for_user(request.user)})
