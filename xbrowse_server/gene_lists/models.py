from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class GeneList(models.Model):
    """
    Arbitrary list of genes
    (actually a set - no dups)
    Usually used for disease gene lists - eg a list of neuromuscular disease genes
    """
    slug = models.SlugField(max_length=40)
    name = models.CharField(max_length=140)
    description = models.TextField()
    is_public = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def num_genes(self):
        return self.genelistitem_set.count()

    def gene_id_list(self):
        return [g.gene_id for g in self.genelistitem_set.all()]

    def get_genes(self):
        return [settings.REFERENCE.get_gene(gene_id) for gene_id in self.gene_id_list()]

    def get_projects(self, user):
        """
        Projects assigned to this gene list,
        """
        return [p for p in self.project_set.all() if p.can_view(user)]

    def get_managers(self):
        pass

    def toJSON(self, details=False):
        d = {
            'slug': self.slug,
            'name': self.name,
            'description': self.description,
            'num_genes': self.num_genes(),
        }
        if details:
            d['genes'] = [
                {
                    'gene_id': item.gene_id,
                    'description': item.description,
                } for item in self.genelistitem_set.all()
            ]
        return d


class GeneListItem(models.Model):
    """
    Entry in a gene list
    """
    gene_id = models.CharField(max_length=20)  # ensembl ID
    gene_list = models.ForeignKey(GeneList)
    description = models.TextField(default="")

