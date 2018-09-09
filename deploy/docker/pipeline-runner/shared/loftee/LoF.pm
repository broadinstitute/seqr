=head1 CONTACT                                                                                                       

 Konrad Karczewski <konradjkarczewski@gmail.com>
 
=cut

=head1 NAME

 LoF

=head1 SYNOPSIS

 mv LoF.pm ~/.vep/Plugins
 perl variant_effect_predictor.pl -i variations.vcf --plugin LoF
 perl variant_effect_predictor.pl -i variations.vcf --plugin LoF,filter_position:0.05,...

=head1 DESCRIPTION

A VEP plugin that filters loss-of-function variation.

=cut

package LoF;

# code for [5,3]UTR_SPLICE and END_TRUNC filters
require "utr_splice.pl";
require "gerp_dist.pl";

# code for splicing predictions
require "de_novo_donor.pl";
require "extended_splice.pl";
require "splice_site_scan.pl";
require "loftee_splice_utils.pl";
require "svm.pl";

use strict;
use warnings;
no if $] >= 5.018, 'warnings', "experimental::smartmatch";

our $debug;

use Bio::EnsEMBL::Variation::Utils::BaseVepPlugin;
use DBI;

use base qw(Bio::EnsEMBL::Variation::Utils::BaseVepPlugin);
use Bio::Perl;
use List::Util qw(sum);

sub get_header_info {
    return {
        LoF => "Loss-of-function annotation (HC = High Confidence; LC = Low Confidence)",
        LoF_filter => "Reason for LoF not being HC",
        LoF_flags => "Possible warning flags for LoF",
        LoF_info => "Info used for LoF annotation",
    };
}

sub feature_types {
    return ['Transcript'];
}

sub new {
    my $class = shift;

    my $self = $class->SUPER::new(@_); # self is a reference to a hash
    
    foreach my $parameter (@{$self->params}) {
        my @param = split /:/, $parameter;
        if (scalar @param == 2) {
            $self->{$param[0]} = $param[1];
        }
    }
    # general LOFTEE parameters
    $self->{filter_position} = 0.05 if !defined($self->{filter_position});
    $self->{min_intron_size} = 15 if !defined($self->{min_intron_size});
    $self->{fast_length_calculation} = 'fast' if !defined($self->{fast_length_calculation});
    $self->{human_ancestor_fa} = 'human_ancestor.fa.rz' if !defined($self->{human_ancestor_fa});
    $self->{check_complete_cds} = 'false' if !defined($self->{check_complete_cds});
    $self->{use_gerp_end_trunc} = 0;  #if !defined($self->{check_complete_cds});
    
    # general splice prediction parameters
    $self->{loftee_path} = '/vep/loftee/' if !defined($self->{loftee_path});
    $self->{get_splice_features} = 1 if !defined($self->{get_splice_features});
    $self->{weak_donor_cutoff} = -4 if !defined($self->{weak_donor_cutoff}); # used for filtering potenital de novo splice events: if the reference site falls below this threshold, skip it
    $self->{donor_motifs} = get_motif_info(catdir($self->{loftee_path}, 'splice_data/donor_motifs')); # returns a hash reference
    $self->{acceptor_motifs} = get_motif_info(catdir($self->{loftee_path}, 'splice_data/acceptor_motifs')); # returns a hash reference

    # MaxEntScan models
    my @metables = &make_max_ent_scores(catdir($self->{loftee_path}, 'maxEntScan/splicemodels/')); # score3
    my %me2x5 = &make_score_matrix(catfile($self->{loftee_path}, 'maxEntScan/me2x5')); # score5
    my %seq = &make_sequence_matrix(catfile($self->{loftee_path}, 'maxEntScan/splicemodels/splice5sequences')); # score5
    $self->{metables} = \@metables;
    $self->{me2x5} = \%me2x5;
    $self->{seq} = \%seq;

    # extended splice parameters
    $self->{donor_disruption_mes_cutoff} = 6 if !defined($self->{donor_disruption_mes_cutoff}); # minimum magnitude of MES disruption to be considered splice-disrupting
    $self->{acceptor_disruption_mes_cutoff} = 7 if !defined($self->{acceptor_disruption_mes_cutoff});
    $self->{donor_disruption_cutoff} = 0.98 if !defined($self->{donor_disruption_cutoff});
    $self->{acceptor_disruption_cutoff} = 0.99 if !defined($self->{acceptor_disruption_cutoff});
    $self->{donor_model} = get_logreg_coefs(catdir($self->{loftee_path}, 'splice_data/donor_model.txt'));  
    $self->{acceptor_model} = get_logreg_coefs(catdir($self->{loftee_path}, 'splice_data/acceptor_model.txt'));  

    # splice site scan parameters
    $self->{max_scan_distance} = 15 if !defined($self->{max_scan_distance}); # maximum distance from the original splice site for a cryptic/rescue splice site 
    $self->{donor_rescue_cutoff} = 8.5 if !defined($self->{donor_rescue_cutoff}); 
    $self->{acceptor_rescue_cutoff} = 8.5 if !defined($self->{acceptor_rescue_cutoff});

    # de novo donor splice parameters
    $self->{exonic_denovo_only} = 1 if !defined($self->{exonic_denovo_only});
    $self->{max_denovo_donor_distance} = 200 if !defined($self->{max_denovo_donor_distance}); # maximum distance from the authentic splice site for a de novo donor splice site
    $self->{denovo_donor_cutoff} = 0.995 if !defined($self->{denovo_donor_cutoff});
    $self->{sre_flanksize} = 100 if !defined($self->{sre_flanksize}); # size of regions upstream/downstream of a splice site in which SREs operate 
    $self->{donor_svm} = get_svm_info(catdir($self->{loftee_path}, 'splice_data/de_novo_donor_SVM')); # returns a hash reference

    # parameters for PHYLOCSF-based filters
    $self->{conservation_file} = 'false';  # if !defined($self->{conservation_file});
    $self->{conservation_database} = 'false';
    if ($self->{conservation_file} ne 'false') {
        if ($self->{conservation_file} eq 'mysql') {
            my $db_info = "DBI:mysql:mysql_read_default_group=loftee;mysql_read_default_file=~/.my.cnf";
            $self->{conservation_database} = DBI->connect($db_info, undef, undef) or die "Cannot connect to mysql using " . $db_info . "\n";
        } else {
            $self->{conservation_database} = DBI->connect("dbi:SQLite:dbname=" . $self->{conservation_file}, "", "") or die "Cannot connect to " . $self->{conservation_file} . "\n";
        }
    }
    # parameters for GERP-based filters
    $self->{tabix_path} = 'tabix' if !defined($self->{tabix_path});
    $self->{gerp_database} = 'false';
    $self->{gerp_file} = '';  #'/vep/loftee/GERP_scores.final.sorted.txt.gz' if !defined($self->{gerp_file});
    if (defined($self->{gerp_file})) {
        if ($self->{gerp_file} eq 'mysql') {
            my $db_info = "DBI:mysql:mysql_read_default_group=loftee;mysql_read_default_file=~/.my.cnf";
            $self->{gerp_database} = DBI->connect($db_info, undef, undef) or die "Cannot connect to mysql using " . $db_info . "\n";
        } else {
            if (`$self->{tabix_path} -l $self->{gerp_file} 2>&1` =~ "fail") {
                die "Cannot read " . $self->{gerp_file} . " using " . $self->{tabix_path};
            } else {
                $self->{gerp_database} = $self->{tabix_path} . " " . $self->{gerp_file};
            }
        }
    }
    $self->{apply_all} = $self->{apply_all} || 'false';
    $debug = $self->{debug} || 0;
    
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
    my $tv = $transcript_variation_allele->transcript_variation;
    my $vf = $transcript_variation_allele->variation_feature;
    
    my @consequences = map { $_->SO_term } @{ $transcript_variation_allele->get_all_OverlapConsequences };
    
    my @filters = ();
    my @flags = ();
    my @info = ();
    
    # Filter in
    unless ($tv->transcript->biotype eq "protein_coding") {
        return {};
    }
    my $confidence = '';
    my $allele = $transcript_variation_allele->allele_string();
    
    my $genic_variant = !("upstream_gene_variant" ~~ @consequences || "downstream_gene_variant" ~~ @consequences);
    my $fiveUTR_variant = check_5UTR($tv, $vf); # includes intronic variants
    my $threeUTR_variant = check_3UTR($tv, $vf);
    my $UTR_variant = $fiveUTR_variant || $threeUTR_variant;
    my $other_lof = "stop_gained" ~~ @consequences || "frameshift_variant" ~~ @consequences;
    my $vep_splice_lof = "splice_acceptor_variant" ~~ @consequences || "splice_donor_variant" ~~ @consequences;
    my $loftee_splice_lof = 0;
    my $lof_position = -1;

    # splice predictions
    if ($genic_variant && !($UTR_variant || $other_lof)) {
        # extended splice - predict whether variant disrupts an annotated splice site
        my @results = get_effect_on_splice($tv, $vf, $allele, $vep_splice_lof, $self);
        my ($splice_disrupting, $feats, $splice_info) = @results;
        if (defined($splice_info)) {
            # record features used for prediction of splice site disruption
            if ($self->{get_splice_features} && defined($feats)) {
                while (my ($key, $value) = each % { $feats }) {
                    push(@info, $key . ":" . $value);
                }
            }

            # if variant is determined to disrupt the splice site, scan for alternative splice sites
            if ($splice_disrupting) {
                $loftee_splice_lof = 1;
                push(@info, $splice_info->{type} . "_DISRUPTING");
                my @results = scan_for_alternative_splice_sites($tv, $vf, $splice_info, $self);
                my ($feats, $loftee_info) = @results;
                if ($self->{get_splice_features}) {
                    while (my ($key, $value) = each % { $feats }) {
                        push(@info, $key . ":" . $value) if defined($value);
                    }
                }
                if ($loftee_info->{rescued}) {
                    push(@filters, $loftee_info->{rescue_tag});
                } else {
                    $lof_position = $loftee_info->{lof_pos};
                } 
            } elsif ($vep_splice_lof) {
                push(@filters, "NON_" . $splice_info->{type} . "_DISRUPTING");
            }
        }

        # de novo donor 
        if (!$splice_disrupting) {
            my @results = check_for_denovo_donor($tv, $vf, $allele, $self); 
            my ($p_denovo, $feat_ref, $lof, $lof_pos) = @results;
            if ($p_denovo > $self->{denovo_donor_cutoff}) {
                push(@info, 'DE_NOVO_DONOR');
                $lof_position = $lof_pos;
                $loftee_splice_lof = $lof;
            }
            if ($p_denovo > 0 && $self->{get_splice_features}) {
                while (my ($key, $value) = each % { $feat_ref }) {
                    push(@info, $key . ":" . $value) unless grep {$_ eq ($key . ":" . $value)} @info;
                }
            }
        }
    }

    if ($loftee_splice_lof || $vep_splice_lof || $other_lof) {
        $confidence = 'HC';
    } else {
        if ($self->{apply_all} eq 'false') {
            return { LoF_info => join(',', @info), LoF_flags => join(',', @flags), LoF_filter => join(',', @filters) };
        }
    }

    # filter LoF variants occurring near the reference stop codon
    if ($tv->cds_end) {
        my $lof_percentile = get_position($tv, $self->{fast_length_calculation});
        # push(@filters, 'END_TRUNC') if ($lof_percentile >= 1-$self->{filter_position});

        # using distance from stop codon weighted by GERP
        #my $slice = $vf->feature_Slice();
        #$lof_position = $slice->start if $lof_position < 0;
        my ($gerp_dist, $dist) = get_gerp_weighted_dist($tv->transcript, $lof_position, $self->{gerp_database}, $self->{conservation_database});
        #push(@info, 'GERP_DIST:' . $gerp_dist);
        push(@info, 'BP_DIST:' . $dist);
        push(@info, 'PERCENTILE:' . $lof_percentile);

        my $last_exon_length = get_last_exon_coding_length($tv);
        my $d = $dist - $last_exon_length;
        push(@info, 'DIST_FROM_LAST_EXON:' . $d);
        push(@info, '50_BP_RULE:' . ($d <= 50 ? 'FAIL' : 'PASS'));
        push(@filters, 'END_TRUNC') if ($d <= 50);  # & ($gerp_dist <= 180);
    }

    # Filter out - exonic
    if ($tv->exon_number) {
        if (check_for_exon_annotation_errors($tv)) {
            push(@filters, 'EXON_INTRON_UNDEF');
        } elsif (check_for_single_exon($tv)) {
            push(@flags, 'SINGLE_EXON');
        } else {
            if (lc($self->{check_complete_cds}) eq 'true') {
                push(@filters, 'INCOMPLETE_CDS') if (check_incomplete_cds($tv));
            }
            push(@flags, 'NON_CAN_SPLICE_SURR') if (check_surrounding_introns($tv, $self->{min_intron_size}));
        }
        
        if (lc($self->{conservation_file}) ne 'false') {
            my $conservation_info = check_for_conservation($transcript_variation_allele, $self->{conservation_database});
            if (not $conservation_info) {
                push(@info, "PHYLOCSF_TOO_SHORT");
            } else {
                push(@info, 'ANN_ORF:' . $conservation_info->{corresponding_orf_score});
                push(@info, 'MAX_ORF:' . $conservation_info->{max_score});
                if ($conservation_info->{corresponding_orf_score} < 0) {
                    my $flag = ($conservation_info->{max_score} > 0) ? ("PHYLOCSF_UNLIKELY_ORF") : ("PHYLOCSF_WEAK");
                    push(@flags, $flag);
                }
            }
        }
    } 

    # Intronic
    if ($tv->intron_number) {
        if (check_for_intron_annotation_errors($tv)) {
            push(@filters, 'EXON_INTRON_UNDEF');
        } else {
            # Intron size filter
            my $intron_size = get_intron_size($tv);
            push(@info, 'INTRON_SIZE:' . $intron_size);           
            push(@filters, 'SMALL_INTRON') if ($intron_size < $self->{min_intron_size});                      
            push(@filters, 'NON_CAN_SPLICE') if (check_for_non_canonical_intron_motif($tv));
            if ("splice_acceptor_variant" ~~ @consequences || "splice_donor_variant" ~~ @consequences) {
                push(@filters, '5UTR_SPLICE') if $fiveUTR_variant;
                push(@filters, '3UTR_SPLICE') if $threeUTR_variant;
            } 
            if ("splice_acceptor_variant" ~~ @consequences) {
                push(@flags, 'NAGNAG_SITE') if (check_nagnag_variant($tv, $vf));
            }
        }
    }

    if (lc($self->{human_ancestor_fa}) ne 'false') {
        push(@filters, 'ANC_ALLELE') if (check_for_ancestral_allele($transcript_variation_allele, $self->{human_ancestor_fa}));
    }
    
    if ($confidence eq 'HC' && scalar @filters > 0) {
        $confidence = 'LC';
    }
    
    return { LoF => $confidence, LoF_filter => join(',', @filters), LoF_flags => join(',', @flags), LoF_info => join(',', @info) };
}

sub DESTROY {
    my $self = shift;
    if ($self->{conservation_file} eq 'mysql') {
        $self->{conservation_database}->disconnect();
    }
}

# Global functions

sub small_intron {
    my $transcript_variation = shift;
    my $intron_number = shift;
    my $min_intron_size = shift;
    my @gene_introns = @{$transcript_variation->transcript->get_all_Introns()};   
    return ($gene_introns[$intron_number]->length < $min_intron_size);
}

sub intron_motif_start {
    my ($transcript_variation, $intron_number) = @_;
    
    my $transcript = $transcript_variation->transcript;
    my @gene_introns = @{$transcript->get_all_Introns()};
    
    # Cache intron sequence
    unless (exists($transcript->{intron_cache}->{$intron_number})) {
        $transcript->{intron_cache}->{$intron_number} = $gene_introns[$intron_number]->seq;
    }
    my $sequence = $transcript->{intron_cache}->{$intron_number};
    
    print "Intron starts with: " . substr($sequence, 0, 2) . "\n" if ($debug && substr($sequence, 0, 2) ne 'GT');
    
    return (substr($sequence, 0, 2) ne 'GT');
}

sub intron_motif_end {
    my ($transcript_variation, $intron_number) = @_;
    
    my $transcript = $transcript_variation->transcript;
    my @gene_introns = @{$transcript->get_all_Introns()};
    
    # Cache intron sequence
    unless (exists($transcript->{intron_cache}->{$intron_number})) {
        $transcript->{intron_cache}->{$intron_number} = $gene_introns[$intron_number]->seq;
    }
    my $sequence = $transcript->{intron_cache}->{$intron_number};
    
    return (substr($sequence, length($sequence) - 2, 2) ne 'AG')
}

sub get_cds_length_fast {
    my $transcript = shift;
    
    my $transcript_cds_length = $transcript->cdna_coding_end - $transcript->cdna_coding_start + 1;
    return $transcript_cds_length;
}

sub get_cds_length {
    my $transcript = shift;
    
    # Cache CDS sequence
    unless (exists($transcript->{cds_seq_cache})) {
        $transcript->{cds_seq_cache} = $transcript->translateable_seq;
    }
    my $transcript_cds_length = length($transcript->{cds_seq_cache});
    return $transcript_cds_length;
}

# Stop-gain and frameshift annotations
sub check_incomplete_cds {
    my $transcript_variation = shift;
    
    my $transcript = $transcript_variation->transcript;
    my $start_annotation = $transcript->get_all_Attributes('cds_start_NF');
    my $end_annotation = $transcript->get_all_Attributes('cds_end_NF');
    
    return (defined($start_annotation) || defined($end_annotation));
}

sub check_for_exon_annotation_errors {
    my $transcript_variation = shift;
    return (!defined($transcript_variation->exon_number))
}

sub get_position {
    my $transcript_variation = shift;
    my $speed = shift;
    
    # 2 ways to get length: fast and approximate, or slow and accurate
    my $transcript_cds_length;
    if ($speed eq 'fast') {
        $transcript_cds_length = get_cds_length_fast($transcript_variation->transcript);
    } else {
        $transcript_cds_length = get_cds_length($transcript_variation->transcript);
    }
    my $variant_cds_position = $transcript_variation->cds_end;
    
    return $variant_cds_position/$transcript_cds_length;
}


sub check_for_single_exon {
    my $transcript_variation = shift;
    my @exons = split /\//, ($transcript_variation->exon_number);
    return ($exons[1] == 1)
}

sub check_surrounding_introns {
    my $transcript_variation = shift;
    my $min_intron_size = shift;
    my ($exon_number, $total_exons) = split /\//, ($transcript_variation->exon_number);
    $exon_number--;
    
    # Check for small introns and GT..AG motif
    # Only next intron if in first exon, only previous intron if in last exon, otherwise both previous and next
    if ($exon_number == 0) {
        return (small_intron($transcript_variation, $exon_number, $min_intron_size) ||
               intron_motif_start($transcript_variation, $exon_number))
    } elsif ($exon_number == $total_exons - 1) {
        return (small_intron($transcript_variation, $exon_number - 1, $min_intron_size) ||
                intron_motif_end($transcript_variation, $exon_number - 1))
    } else {
        return (small_intron($transcript_variation, $exon_number, $min_intron_size) ||
                small_intron($transcript_variation, $exon_number - 1, $min_intron_size) ||
                intron_motif_start($transcript_variation, $exon_number) ||
                intron_motif_end($transcript_variation, $exon_number - 1))
    }
}

# Splicing annotations
sub check_nagnag_variant {
    my $transcript_variation = shift;
    my $variation_feature = shift;
    
    # Cache splice sites
    unless (exists($variation_feature->{splice_context_seq_cache})) {
        my $seq = uc($variation_feature->feature_Slice->expand(4, 4)->seq);
        $seq = ($transcript_variation->transcript->strand() == -1) ? reverse_complement($seq)->seq() : $seq;
        $variation_feature->{splice_context_seq_cache} = $seq;
    }
    my $sequence = $variation_feature->{splice_context_seq_cache};
    
    # Only consider NAGNAG sites for SNPs for now
    if (length($sequence) == 9) {
        return ($sequence =~ m/AG.AG/);
    } else {
        return 0;
    }
}

sub check_for_intron_annotation_errors {
    my $transcript_variation = shift;
    return (!defined($transcript_variation->intron_number))
}

sub get_intron_size {
    my $transcript_variation = shift;
    my ($intron_number, $total_introns) = split /\//, ($transcript_variation->intron_number);
    $intron_number--;
    my @gene_introns = @{$transcript_variation->transcript->get_all_Introns()};

    return ($gene_introns[$intron_number]->length);
}

sub check_for_non_canonical_intron_motif {
    my $transcript_variation = shift;
    my ($intron_number, $total_introns) = split /\//, ($transcript_variation->intron_number);
    $intron_number--;
    return (intron_motif_start($transcript_variation, $intron_number) || intron_motif_end($transcript_variation, $intron_number))
}

sub check_for_ancestral_allele {
    my $transcript_variation_allele = shift;
    my $human_ancestor_location = shift;
    my $variation_feature = $transcript_variation_allele->variation_feature;
    
    # Ignoring indels for now
    if (($variation_feature->allele_string =~ /-/) or (length($variation_feature->allele_string) != 3)) {
        return 0;
    }
    
    my $aff_allele = $transcript_variation_allele->variation_feature_seq;
    
    # Get ancestral allele from human_ancestor.fa.rz
    my $region = $variation_feature->seq_region_name() . ":" . $variation_feature->seq_region_start() . '-' . $variation_feature->seq_region_end();
    my $faidx = `samtools faidx $human_ancestor_location $region`;
    my @lines = split(/\n/, $faidx);
    shift @lines;
    my $ancestral_allele = uc(join('', @lines));
    
    return ($ancestral_allele eq $aff_allele)
}

sub check_for_conservation {
    my $transcript_variation_allele = shift;
    my $conservation_db = shift;
    my $transcript_variation = $transcript_variation_allele->transcript_variation;
    
    # Get exon info
    my $transcript_id = $transcript_variation_allele->transcript_variation->transcript->stable_id();
    my ($exon_number, $total_exons) = split /\//, ($transcript_variation->exon_number);
    # Check if exon is conserved
    my $sql_statement = $conservation_db->prepare("SELECT * FROM phylocsf_data WHERE transcript = ? AND exon_number = ?;");
    $sql_statement->execute($transcript_id, $exon_number) or die("MySQL ERROR: $!");
    my $results = $sql_statement->fetchrow_hashref;
    $sql_statement->finish();
    return $results;
}

sub get_last_exon_coding_length {
    my $transcript_variation = shift;
    my ($exon_idx, $number_of_exons) = split /\//, ($transcript_variation->exon_number);
    $exon_idx--;
    my @exons = @{ $transcript_variation->transcript->get_all_Exons };

    my $strand = $transcript_variation->transcript->strand();
    my $stop_codon_pos = 0;
    if ($strand == 1) {
        $stop_codon_pos = $transcript_variation->transcript->{coding_region_end};
    } elsif ($strand == -1) {
        $stop_codon_pos = $transcript_variation->transcript->{coding_region_start};
    }
    # locate last exon in CDS, get the length of its coding portion
    my $last_exon_len = -1000;
    for (my $i=$number_of_exons - 1; $i >= $exon_idx; $i--) {
        my $current_exon = $exons[$i];
        if ($strand == 1) {
            if ($current_exon->{start} > $stop_codon_pos) {
                next;
            } elsif ($current_exon->{end} >= $stop_codon_pos) {
                $last_exon_len = $stop_codon_pos - $current_exon->{start};
                last;
            }
        } else {
            if ($current_exon->{end} < $stop_codon_pos) {
                next;
            } elsif ($current_exon->{start} <= $stop_codon_pos) {
                $last_exon_len = $current_exon->{end} - $stop_codon_pos;
                last;
            }
        }
    }
    return $last_exon_len;
}

1;
