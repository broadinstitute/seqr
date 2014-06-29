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
