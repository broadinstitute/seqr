from oauth2_provider.middleware import OAuth2TokenMiddleware


class DisableCsrfOAuth2TokenMiddleware:
    """
    Extension of OAuth2TokenMiddleware that disables CSRF (if Bearer token is provided) before delegating to actual
    OAuth2TokenMiddleware().  Bearer tokens themselves are verified with IDP and CSRF is not applicable in this context.
    """

    def __init__(self, get_response):
        self.oauth2_token_middleware = OAuth2TokenMiddleware(get_response)

    def __call__(self, request):
        if request.META.get("HTTP_AUTHORIZATION", "").startswith("Bearer"):
            setattr(request, '_dont_enforce_csrf_checks', True)

        return self.oauth2_token_middleware(request)
