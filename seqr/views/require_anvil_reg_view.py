from django.http import HttpResponse

def require_anvil_registration(request, *args, **kwargs):
    return HttpResponse('<p>Logging in has failed.</p><p>Make sure you have registered your account on AnVIL. Click '
            '<a href=https://anvil.terra.bio>https://anvil.terra.bio</a> to sign in with Google and register your account.</p>'
            '<a href=/login>Return</a>')
