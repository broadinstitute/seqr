=head1 CONTACT                                                                                                       

 Konrad Karczewski <konradjkarczewski@gmail.com>
 
=cut

=head1 NAME

 ancestral

=head1 SYNOPSIS

 mv ancestral.pm ~/.vep/Plugins
 perl variant_effect_predictor.pl -i variations.vcf --plugin ancestral
 perl variant_effect_predictor.pl -i variations.vcf --plugin ancestral,human_ancestor.fa.gz

=head1 DESCRIPTION

 A VEP plugin that writes the ancestral allele from the variant (SNPs only!).

=cut

package ancestral;

use strict;
use warnings;

use Bio::EnsEMBL::Variation::Utils::BaseVepPlugin;
use base qw(Bio::EnsEMBL::Variation::Utils::BaseVepPlugin);
use Bio::Perl;

sub get_header_info {
    return {
        ancestral => "ancestral allele"
    };
}

sub feature_types {
    return ['Feature', 'Intergenic'];
}

sub new {
    my $class = shift;

    my $self = $class->SUPER::new(@_);
    
    foreach my $parameter (@{$self->params}) {
        my @param = split /:/, $parameter;
        if (scalar @param == 2) {
            $self->{$param[0]} = $param[1];
        }
    }
    
    $self->{human_ancestor_fa} = $self->{human_ancestor_fa} || 'human_ancestor.fa.rz';
    
    return $self;
}

sub run {
    my ($self, $transcript_variation_allele) = @_;
    my $human_ancestor_location = $self->{human_ancestor_fa};
    my $variation_feature = $transcript_variation_allele->variation_feature;
    
    # Ignoring indels for now
    if (($variation_feature->allele_string =~ /-/) or (length($variation_feature->allele_string) != 3)) {
        return {};
    }
    
    # Get ancestral allele from human_ancestor.fa.rz
    my $region = $variation_feature->seq_region_name() . ":" . $variation_feature->seq_region_start() . '-' . $variation_feature->seq_region_end();
    my $faidx = `samtools faidx $human_ancestor_location $region`;
    my @lines = split(/\n/, $faidx);
    shift @lines;
    my $ancestral_allele = uc(join('', @lines));
    
    return { ancestral => $ancestral_allele };
}

1;