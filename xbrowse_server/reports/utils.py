from django.http import HttpResponse


def xls_to_response(xls, fname):
    response = HttpResponse(content_type="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename=%s' % fname
    xls.save(response)
    return response

def family_search_report(variants, family):
    raise NotImplementedError