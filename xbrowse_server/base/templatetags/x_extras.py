from django import template
register = template.Library()


def key(d, key_name):
    return d.get(key_name)
key = register.filter('key', key)

def forindex(a, index):
    return a[index]

def phenotype(individual, slug):
    return individual.phenotype_display(slug)

forindex = register.filter('forindex', forindex)
phenotype = register.filter('phenotype', phenotype)


# from http://www.sprklab.com/notes/13-passing-arguments-to-functions-in-django-template

# example: To call multiple arguments do {{ batteries|args:arg1|args:arg2|call:"getPrice" }}.
def callMethod(obj, methodName):
    method = getattr(obj, methodName)

    if obj.__dict__.has_key("__callArg"):
        ret = method(*obj.__callArg)
        del obj.__callArg
        return ret
    return method()

def args(obj, arg):
    if not obj.__dict__.has_key("__callArg"):
        obj.__callArg = []
    
    obj.__callArg += [arg]
    return obj

register.filter("call", callMethod)
register.filter("args", args)