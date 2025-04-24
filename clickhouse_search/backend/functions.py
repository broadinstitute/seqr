from django.db.models import Func

class Array(Func):
    function = 'array'