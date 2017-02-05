
from django.db import models

from xbrowse_server.base.models import Project, Individual
from xbrowse.core import genomeloc

class BreakpointFile(models.Model):
    project = models.ForeignKey(Project, blank=True)
    file_path = models.CharField(max_length=500, default="", blank=True)

    class Meta:
        db_table="base_breakpointfile"

class Breakpoint(models.Model):
    project = models.ForeignKey(Project, null=False)
    individual = models.ForeignKey(Individual, null=False)
    xpos = models.BigIntegerField(db_index=True)

    # depth   cscore  partner genes   cdsdist
    obs = models.IntegerField(db_index=True)
    sample_count = models.IntegerField(db_index=True)
    consensus = models.FloatField()
    partner = models.TextField(blank=True, null=True)

    class Meta:
        db_table="base_breakpoint"

    def toList(self):
        genes = [{ 'gene' : bg.gene_symbol, 'cds_dist': bg.cds_dist } for bg in self.breakpointgene_set.all()]

        chr,pos = genomeloc.get_chr_pos(self.xpos)
        return [
            self.xpos,
            chr,
            pos,
            self.obs,
            self.sample_count,
            self.consensus,
            self.partner,
            self.individual.indiv_id,
            genes,
        ]

    def toDict(self):
        genes = [{ 'gene' : bg.gene_symbol, 'cds_dist': bg.cds_dist } for bg in self.breakpointgene_set.all()]

        chr,pos = genomeloc.get_chr_pos(self.xpos)
        return {
            'xpos' : self.xpos,
            'chr' : chr,
            'pos' : pos,
            'obs' : self.obs,
            'sample_count' : self.sample_count,
            'consensus' : self.consensus,
            'indiv_id' : self.individual.indiv_id,
            'genes' : genes,
        }

class BreakpointMetaData(models.Model):
    breakpoint = models.ForeignKey(Breakpoint, null=False)
    type = models.TextField(blank=True, default="")
    tags = models.TextField(blank=True, default="")

    class Meta:
        db_table="base_breakpointmetadata"

    def toDict(self):
        return {
           'breakpoint_id' : self.breakpoint.xpos,
           'type' : self.type,
           'tags' : self.tags
        } 

class BreakpointGene(models.Model):
    breakpoint = models.ForeignKey(Breakpoint, null=False)
    gene_symbol = models.CharField(db_index=True,max_length=20)  # HGNC symbol
    cds_dist = models.IntegerField()

    class Meta:
        db_table="base_breakpointgene"

