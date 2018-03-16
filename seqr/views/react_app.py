from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def main_app(request):
    """Loads the react single page app."""

    return render(request, 'app.html')
