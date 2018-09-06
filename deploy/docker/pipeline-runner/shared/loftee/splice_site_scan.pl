use strict;
use List::Util qw[min max];

# origin of scan occurs at the original GT/AG, unless the original GT/AG is disrupted, 
# in which case the origin of scan should occur at the first remaining base from the original exon that preserves the exon's reading frame
sub scan_for_alternative_splice_sites {
    my ($tv, $vf, $info, $cache) = @_[0..3];

    # initialize some variables
    my %info = % { $info };
    my $cutoff = 0;

    # transcript info
    my $tr = $tv->transcript;
    my $ensembl_id = $tr->stable_id;
    my @exons = @{ $tr->get_all_Exons };
    my @introns = @{ $tr->get_all_Introns };
    my $exon = $exons[$info->{exon_idx}];
    my $intron = $introns[$info->{intron_idx}];
    my $strand = $tr->strand();
    
    # mutation info
    my $slice = $vf->feature_Slice();
    my $allele = $info->{allele};
    
    # splice site info
    my $type = $info->{type};
    my $donor = $type eq "DONOR";
    my $ref_mes = $info->{ref_mes};

    # define boundaires of nucleotide sequence
    my ($seq_lb, $seq_rb);
    if ($donor) { 
        # from beginning of the exon to the end of the intron
        if ($strand == 1) {
            $seq_lb = $exon->start - 200;
            $seq_rb = $intron->end + 200;
        } else {
            $seq_lb = $intron->start - 200;
            $seq_rb = $exon->end + 200;
        }
        $cutoff = $cache->{donor_rescue_cutoff};
    } else {
        # from the beginning of the intron to the exon of the exon
        if ($strand == 1) {
            $seq_lb = $intron->start - 200;
            $seq_rb = $exon->end + 200;
        } else {
            $seq_lb = $exon->start - 200;
            $seq_rb = $intron->end + 200;
        }
        $cutoff = $cache->{acceptor_rescue_cutoff};
    }

    # get nucleotide sequence
    my $left = $slice->start - $seq_lb;
    my $right = $seq_rb - $slice->end;
    $slice->{strand} = 1; # weird hack, not sure if neccessary
    my $wt = uc($slice->expand($left, $right)->seq());
    my $upstream_flank = $left;
    if ($strand == -1) {
        $wt = reverse_complement($wt)->seq();
        $upstream_flank = $right;
    }
    my ($var, $nt_delta) = mutate_seq($wt, $allele, $strand, $upstream_flank);
    
    # determine how the mutation affects the length of the exon
    my $exon_delta = 0;
    if ($tv->exon_number || !$tv->intron_number) {
        if ($nt_delta < 0) { # deletion
            if ($donor) {
                if ($strand == 1) {
                    $exon_delta = $slice->start - $intron->start + max(0, $intron->start - $slice->end - 1);
                } else {
                    $exon_delta = $intron->end - $slice->end + max(0, $slice->start - $intron->end - 1);
                }
            } elsif ($strand == 1) { # acceptor
                $exon_delta = $intron->end - $slice->end + max(0, $slice->start - $intron->end - 1);
            } else {
                $exon_delta = $slice->start - $intron->start + max(0, $intron->start - $slice->end - 1);
            }
        }  else { # insertion
            $exon_delta = $nt_delta;
        }
    }

    # find best respective rescue / cryptic sites
    my @sites = scan_for_splice_sites($tr, $var, \%info, $exon_delta, $cache);
    my %features = (
        "CRYPTIC_" . $type . "_POS" => undef,
        "CRYPTIC_" . $type . "_MES" => undef,
        "RESCUE_" . $type . "_POS" => undef,
        "RESCUE_" . $type . "_MES" => undef
        );

    foreach my $arr_ref (@sites) {
        my @site = @ { $arr_ref };
        my ($dist, $lof, $mes, $seq) = @site;
        if ($lof) {
            my $best_mes = $features{"CRYPTIC_" . $type . "_MES"};
            if (!(defined($best_mes)) || ($mes > $best_mes)) {
                $features{"CRYPTIC_" . $type . "_MES"} = $mes;
                $features{"CRYPTIC_" . $type . "_POS"} = $dist;
            }
        } else {
            my $best_mes = $features{"RESCUE_" . $type . "_MES"};
            if (!(defined($best_mes)) || ($mes > $best_mes)) {
                $features{"RESCUE_" . $type . "_MES"} = $mes;
                $features{"RESCUE_" . $type . "_POS"} = $dist;
            }
        }
    }

    my $rescue_mes = $features{"RESCUE_" . $type . "_MES"};
    my $cryptic_mes = $features{"CRYPTIC_" . $type . "_MES"};
    my %loftee_info = (
        "rescue_tag" => "RESCUE_" . $type,
        "rescued" => defined($rescue_mes) && ($rescue_mes > $cutoff),
        "lof_pos" => (($donor && $strand == 1) || (!$donor && $strand != 1)) ? $exon->end : $exon->start # for donors, lof_pos = donor+1 position. for acceptors, acceptor-1
        );

    return (\%features, \%loftee_info);
}

sub scan_for_splice_sites {
    my ($tr, $seq, $info, $exon_delta, $cache) = @_[0..4];
    # initialize some variables
    my %info = % { $info };
    my $donor = $info->{type} eq "DONOR";
    my $exon_idx = $info->{exon_idx};
    my @exons = @{ $tr->get_all_Exons };
    my $exon = $exons[$exon_idx];
    my $exon_length = $exon->end - $exon->start + 1;

    # need these for determining if splice site introduces stop codon
    my $cds_dist = get_cds_dist_to_exon($tr, $exon_idx);
    my $leading_frame = (3 - ($cds_dist % 3)) % 3; # Number of bases to complete the final codon of the previous exon
    if ($donor) {
        my $tailing_frame = ($exon_length - $leading_frame) % 3; # Number of bases to begin the first codon of the next exon
        my $next_exon = $exons[$exon_idx + 1];
        my $next_exon_seq = $next_exon->seq->seq;
        my $codon_completion = substr $next_exon_seq, 0, 3 - $tailing_frame;
        return scan_for_donors($seq, $codon_completion, $exon_length, $exon_delta, $cache);
    } else {
        my $previous_exon = $exons[$exon_idx - 1];
        my $prev_exon_seq = $previous_exon->seq->seq;
        my $codon_completion = substr $prev_exon_seq, -(3 - $leading_frame); 
        return scan_for_acceptors($seq, $codon_completion, $exon_length, $exon_delta, $cache);
    }
}

# Scan forwards starting in exon and ending in intron. As you scan, keep track of new codons being accumulated.
sub scan_for_donors {
    my ($seq, $codon_completion, $exon_length, $exon_delta, $cache) = @_[0..6];
    # for determining if rescue or LoF
    my @stop_codons = ("TAG", "TAA", "TGA"); 
    my $tailing_frame = 3 - length($codon_completion); 
    my $stop_introduced = 0;
    
    # for scanning
    my $effective_exon_length = $exon_length + $exon_delta;
    my $origin = 200 + $effective_exon_length; # splice junction
    my $w = $cache->{max_scan_distance}; # size of scanning window
    my $start = max($origin - 3 - $w, 200); # scan must remain within exon
    my $end = $origin - 3 + $w + 1; # and within intron
    my @sites = ();
    
    # for splice site features
    my $flanksize = $cache->{sre_flanksize};
    my $motifs = $cache->{donor_motifs}; # SREs

    for (my $i=$start; $i < $end; $i++) {
        my $consensus = substr $seq, $i, 9;
        my $junc = $i + 3;
        my $current_intron_length = length($seq) - 200 - $junc;
        last if ($current_intron_length < 70);

        next if (length($consensus) != 9 || $consensus =~ /.*N.*/); # skip if MES score can't be computed 
        my $mes = mes_donor_cache($cache, $consensus);
        my $dist = $junc - $origin; # positive means exon extension, negative means exon truncation
        my $current_exon_length = $junc - 200;

        # determine if a premature stop codon is introduced by the new splice site
        my $inframe = abs ($exon_length - $current_exon_length) % 3 == 0;
        my $lof = 0;
        if ($inframe) {
            my $current_codon = '';
            if ($dist > 0 && !$stop_introduced) {
                my $x = substr $seq, $junc - 3, 3;
                my $introduced_codon = substr $seq, $junc - $tailing_frame - 3, 3;
                $stop_introduced = 1 if $introduced_codon ~~ @stop_codons;
            }
            $current_codon = (substr $seq, $junc - $tailing_frame, $tailing_frame) . $codon_completion;
            $lof = $stop_introduced || $current_codon ~~ @stop_codons;
        } else {
            $lof = 1;
        }
        push(@sites, [$dist, $lof, $mes, $consensus])
    }
    return @sites;
}

# Scan backwards, starting in exon and ending in intron. 
sub scan_for_acceptors {
    my ($seq, $codon_completion, $exon_length, $exon_delta, $cache) = @_[0..4];
    
    # for determining if rescue or LoF
    my @stop_codons = ("TAG", "TAA", "TGA");
    my $leading_frame = 3 - length($codon_completion);
    my $stop_introduced = 0;
    
    # for scanning
    my $effective_exon_length = $exon_length + $exon_delta;
    my $origin = length($seq) - 200 - $effective_exon_length; # splice junction
    my $w = $cache->{max_scan_distance};
    my $start = max($origin - 20 - $w, 200); # scan must remain within intron
    my $end = $origin - 20 + $w; # and within exon
    my @sites = ();

    for (my $i=$end; $i >= $start; $i--) { # scanning backwards
        my $consensus = substr $seq, $i, 23;
        my $junc = $i + 20;
        my $current_intron_length = $junc + 1 - 200;
        last if ($current_intron_length < 70);

        next if (length($consensus) != 23 || $consensus =~ /.*N.*/); # skip if MES score can't be computed 
        my $mes = mes_acceptor_cache($cache, $consensus);
        my $dist = $junc - $origin; # positive dist means exon truncation, negative dist means exon extension
        my $current_exon_length = length($seq) - 200 - $junc;

        # determine if a premature stop codon is introduced by the new splice site
        my $inframe = abs ($exon_length - $current_exon_length) % 3 == 0;
        my $lof = 0;
        if ($inframe) {
            my $current_codon = '';
            if ($dist < 0 && !$stop_introduced) {
                my $introduced_codon = substr $seq, $junc + $leading_frame, 3;
                $stop_introduced = 1 if $introduced_codon ~~ @stop_codons;
            }
            $current_codon = $codon_completion . (substr $seq, $junc, $leading_frame);
            $lof = $stop_introduced || $current_codon ~~ @stop_codons;
        } else {
            $lof = 1;
        }
        push(@sites, [$dist, $lof, $mes, $consensus])
    }
    return @sites;
}



1;