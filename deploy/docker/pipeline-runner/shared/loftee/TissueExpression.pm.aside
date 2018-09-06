=head1 CONTACT                                                                                                       

 Konrad Karczewski <konradjkarczewski@gmail.com>
 
=cut

=head1 NAME

 TissueExpression

=head1 SYNOPSIS

 mv TissueExpression.pm ~/.vep/Plugins
 perl variant_effect_predictor.pl -i variations.vcf --plugin TissueExpression

=head1 DESCRIPTION

 A VEP plugin that overlays GTEx data on transcripts.
 Requires DBD::SQLite (>=1.4.2).

=cut

package TissueExpression;

use strict;
use warnings;

our $debug = 1;
our $ddebug = 0;

use Bio::EnsEMBL::Variation::Utils::BaseVepPlugin;
use DBI;

use base qw(Bio::EnsEMBL::Variation::Utils::BaseVepPlugin);

sub get_header_info {
    return {
        TissueExpression => "GTEx data"
    };
}

sub feature_types {
    return ['Transcript'];
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
    
    $self->{db_location} = $self->{db_location} || 'gtex.db';
    $self->{tissues} = $self->{tissues} || 'all';
    $self->{expressed_cutoff} = $self->{expressed_cutoff} || 0.1;
    if ($self->{db_location} eq 'mysql') {
        my $db_info = "DBI:mysql:mysql_read_default_group=loftee;mysql_read_default_file=~/.my.cnf";
        $self->{database} = DBI->connect($db_info, undef, undef) or die "Cannot connect to mysql using " . $db_info . "\n";
    } else {
        $self->{database} = DBI->connect("dbi:SQLite:dbname=" . $self->{db_location}, "", "") or die "Cannot find gtex.db\n";
    }
    $self->{tissues_only} = $self->{tissues_only} || 'false';
    
    if ($debug) {
        print "Read LOFTEE parameters\n";
        while (my ($key, $value) = each(%$self)) {
            print $key . " : " . $value . "\n";
        }
    }
    
    return $self;
}

sub run {
    my ($self, $transcript_variation_allele) = @_;
    
    my $transcript = $transcript_variation_allele->transcript_variation->transcript;
    
    my $transcript_tissue;
    if (exists($transcript->{expression_cache})) {
        $transcript_tissue = $transcript->{expression_cache};
    } else {
        my $sql_statement;
        if ($self->{tissues} eq 'all') {
            $sql_statement = $self->{database}->prepare("SELECT * FROM tissues WHERE transcript = ?");
            $sql_statement->execute($transcript->stable_id());
        } else {
            my @sql_parameters = split /,/, $self->{tissues};
            $sql_statement = $self->{database}->prepare("SELECT * FROM tissues WHERE transcript = ? AND tissue IN " . join(', ', ('?') x @sql_parameters));
            unshift(@sql_parameters, $transcript->stable_id());
            $sql_statement->execute(@sql_parameters);
        }
        
        my @tissue_entries = ();
        while (my $entry = $sql_statement->fetchrow_hashref) {
            $entry->{tissue} =~ s/ /_/g;
            if ($entry->{expression} > $self->{expressed_cutoff}) {
                unless (lc($self->{tissues_only}) eq 'false') {
                    push(@tissue_entries, $entry->{tissue});
                } else {
                    push(@tissue_entries, $entry->{tissue} . ":" . $entry->{expression});
                }
            }
        }
        $transcript_tissue = join("&", @tissue_entries);
        
        print "Tissues: " . $transcript_tissue . "\n" if $ddebug;
        $transcript->{expression_cache} = $transcript_tissue;
    }

    return { TissueExpression => $transcript_tissue };
}

1;