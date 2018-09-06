use strict;
use List::Util qw[min max];

# variant splice site is assumed to occur at the same AG or GT used by the wild-type splice site
sub get_effect_on_splice {
    my ($tv, $vf, $allele, $splice_lof, $cache) = @_[0..4];

    my $slice = $vf->feature_Slice();
    my ($intron, $intron_idx, $affected_ss, $splice_lb, $splice_rb) = check_if_extended_splice_variant($tv, $slice);
    return (0, undef, undef) if $affected_ss == 0; # if variant does not overlap an extended splice site

     # get consensus splice sequence in reference
    my $strand = $tv->transcript->strand();
    my $left = $slice->start - $splice_lb;
    my $right = $splice_rb - $slice->end;
    $slice->{strand} = 1; # weird hack, not sure if neccessary but I put it in for some reason I can't remember and I'm scared to take it out
    my $wt = uc($slice->expand($left, $right)->seq());
    $wt = reverse_complement($wt)->seq() if ($strand == -1); # reference splice site sequence
    my @flanks = ($left, $right);

    # get MES score for reference site
    my $type = ($affected_ss == 5) ? "DONOR" : "ACCEPTOR";
    my $donor = $type eq "DONOR";
    my $mes = ($donor) ? \&mes_donor_cache : \&mes_acceptor_cache;  
    my $ss_length = ($donor) ? 9 : 23;
    #print "$wt\n";
    return (0, undef, undef) if (length($wt) != $ss_length || $wt =~ /.*N.*/); # quit if MES score can't be computed 
    my $ref_mes = $mes->($cache, $wt);

    # prepare return data for (potential) ensuing scan 
    my %info = ("type" => $type,
                "intron_idx" => $intron_idx, 
                "exon_idx" => ($donor) ? $intron_idx : $intron_idx + 1,
                "allele" => $allele,
                "ref_mes" => $ref_mes,
                "ref_seq" => $wt);

    # get implicated exon
    my $tr = $tv->transcript;
    my @exons = @{ $tr->get_all_Exons };
    my $exon = $exons[$info{exon_idx}];

    # always scan for alternatives in case of indels affecting the essential splice site 
    my $indel = $allele =~ "-";
    return (1, undef, \%info) if ($indel && $splice_lof); 

    # get variant splice site now (i.e. the splice site after incorporating the mutation)
    my $upstream_flank = $left;
    $upstream_flank = $right if ($strand == -1);
    my ($var, $nt_delta) = mutate_seq($wt, $allele, $strand, $upstream_flank);
    if ($nt_delta < 0) {
        my ($ref, $alt) = split /\//, ($allele);
        if (($slice->end - $slice->start + 1) != length($ref)) {
            my %lof_info_error_msg = ( ERROR => "VariationFeature slice inconsistent with allele (try splitting multi-allelic sites?)" );
            return (0, \%lof_info_error_msg, 1);
        }
    }
    my $delta = length($var) - length($wt);

    # deal with deletions
    if ($delta < 0) {
        if ($strand == 1) {
            if (($tv->exon_number && $donor) || ($tv->intron_number && !$donor)) {
                # first addend extends region to the end of the deletion 
                # second addend compensates for missing bases
                $left = $left - ($left < 0)*$left - $delta; 
            } else {
                $right = $right - ($right < 0)*$right - $delta;
            }
        } elsif ($strand == -1) {
            if (($tv->intron_number && $donor) || ($tv->exon_number && !$donor)) {
                $left = $left - ($left < 0)*$left - $delta;
            } else {
                $right = $right - ($right < 0)*$right - $delta;
            }
        }
        my $input = uc($slice->expand($left, $right)->seq());
        my $upstream_flank = $left;
        if ($strand == -1) {
            $input = reverse_complement($input)->seq();
            $upstream_flank = $right;
        }
        ($var, $nt_delta) = mutate_seq($input, $allele, $strand, $upstream_flank);

    # deal with insertions
    } elsif ($delta > 0) {
        my $exonic = $tv->exon_number || ! $tv->intron_number;
        if (($exonic && $donor) || (!$exonic && !$donor)) { # exonic donor OR intronic acceptor
            $var = substr $var, $delta; # remove bases from the beginning of string
            if ($strand == 1) {
                $left = $left - $delta;
            } else {
                $right = $right - $delta;
            }
        } else { # intronic donor OR exonic acceptor
            $var = substr $var, 0, length($var) - $delta; # remove bases from the end of string
            if ($strand == 1) {
                $right = $right - $delta;
            } else {
                $left = $left - $delta;
            }
        }
    }
    return (0, undef, undef) if (length($var) != $ss_length || $var =~ /.*N.*/); # quit if MES score can't be computed 
    push(@flanks, ($left, $right)); # use these for getting SRE features

    # get branch point feature
    my $bp_dist = 'NA';
    if (!$donor) {
        $bp_dist = 60; # this is the farthest away we will look
        my $flank = get_upstream_acceptor_flank($slice, [$left, $right], 43, $strand, $allele);
        while ($flank =~ /[CT]T[AGCT]A[CT]/g) {
            my $pos = $-[0]; # where branch point sequence starts
            my $d = length($flank) - $pos - 3; # distance from splice junction to the necessary A in the branch point sequence
            $bp_dist = $d if $d > 15;
        };
    }

    # get MES features
    my $var_mes = $mes->($cache, $var);
    my $mes_diff = $ref_mes - $var_mes;

    # get GERP feature 
    my $gerp_diff = 'NA';
    if ($cache->{conservation_file} ne 'false') {
        my @pos = get_mutated_bases($wt, $var, $splice_lb, $splice_rb, $strand, $delta);
        my $chrom = $tv->transcript->seq_region_name();
        my @lgerp = map { get_bp_gerp($chrom, $_, $cache->{gerp_database}) } @pos;
        $gerp_diff = (scalar @lgerp > 0) ? sum(@lgerp) : 0;
    }

    # get stuff for SRE features
    my $motifs = ($donor) ? $cache->{donor_motifs} : $cache->{acceptor_motifs} ;
    my $flanksize = $cache->{sre_flanksize};
    my ($ex, $in) = get_sre_flanks($slice, [$left, $right], $strand, $allele, $flanksize, $donor);

    # initialize feature vector
    my %features = (
        $type . "_ESE" => scan_seq($motifs, $ex, 'ese'),
        $type . "_ESS" => scan_seq($motifs, $ex, 'ess'),
        $type . "_ISE" => scan_seq($motifs, $in, 'ise'),
        $type . "_ISS" => scan_seq($motifs, $in, 'iss'),
        $type . "_MES_DIFF" => $mes_diff,
        $type . "_GERP_DIFF" => $gerp_diff,
        "BRANCHPOINT_DISTANCE" => $bp_dist,
        "INTRON_START" => $intron->start,
        "INTRON_END" => $intron->end,
        "EXON_START" => $exon->start,
        "EXON_END" => $exon->end,
        "MUTANT_" . $type . "_MES" => $var_mes
    );

    my ($cutoff, $score) = (0, 0);
    if ($donor) {
        if ($gerp_diff eq 'NA') {
            $cutoff = $cache->{donor_disruption_mes_cutoff};
            $score = $mes_diff;
        } else {
            $cutoff = $cache->{donor_disruption_cutoff};
            $score = logreg(\%features, $cache->{donor_model});
            $features{$type . "_DISRUPTION_PROB"} = $score;
        }
    } else {
        if ($gerp_diff eq 'NA') {
            $cutoff = $cache->{acceptor_disruption_mes_cutoff};
            $score = $mes_diff;
        } else {
            $cutoff = $cache->{acceptor_disruption_cutoff};
            $score = logreg(\%features, $cache->{acceptor_model});
            $features{$type . "_DISRUPTION_PROB"} = $score;
        }
    }
    my $disruptive = $score > $cutoff;
    return ($disruptive, \%features, \%info);
}


# CODE FOR GETTING SRE FEATURES

sub get_sre_flanks {
    my ($slice, $flanks, $strand, $allele, $flanksize, $donor) = @_;
    my ($left, $right) = @ { $flanks };  
    my $pre_alt = uc($slice->expand($left + $flanksize, $right + $flanksize)->seq());
    my $upstream_flank = $left + $flanksize;
    if ($strand != 1) {
        $pre_alt = reverse_complement($pre_alt)->seq();
        $upstream_flank = $right + $flanksize;
    }
    my ($alt, $null) = mutate_seq($pre_alt, $allele, $strand, $upstream_flank);
    my $up = substr $alt, 0, $flanksize;
    my $down = substr $alt, -$flanksize;
    if ($donor) {
        return ($up, $down);
    } else {
        return ($down, $up);
    }
}

# CODE FOR GETTING BRANCHPOINT FEATURE

sub get_upstream_acceptor_flank {
    my ($slice, $flanks, $flank_extension, $strand, $allele) = @_;
    my ($left, $right) = @ { $flanks };  
    if ($strand == 1) {
        $left = $left + $flank_extension;
    } else {
        $right = $right + $flank_extension;
    }
    my $pre_alt = uc($slice->expand($left, $right)->seq());
    my $upstream_flank = $left;
    if ($strand != 1) {
        $pre_alt = reverse_complement($pre_alt)->seq();
        $upstream_flank = $right;
    }
    my ($alt, $null) = mutate_seq($pre_alt, $allele, $strand, $upstream_flank);
    return substr $alt, 0, length($alt) - 3; # return intronic sequence upstream of acceptor junction
}


# CODE FOR GETTING GERP FEATURE

# determine which bases of the extended splice are altered by the variant, return altered positions
sub get_mutated_bases {
    my ($wt, $var, $lb, $rb, $strand) = @_[0..4];
    my @pos = ();
    for(0 .. length($wt)) {
        my $wtbase = substr($wt, $_, 1);
        my $varbase = substr($var, $_, 1);
        if($wtbase ne $varbase) {
            push(@pos, convert_to_coord($_, $lb, $rb, $strand));
        } 
    }
    return @pos;
}

# helper function for get_mutated_bases
sub convert_to_coord {
    my ($x, $lb, $rb, $strand) = @_[0..3];
    if ($strand > 0) {
        return $lb + $x;
    } else {
        return $rb - $x;
    }
}

# CODE FOR LOGISTIC REGRESSION USING MES + GERP

# read file containing constants for logistic regression
sub get_logreg_coefs {
    my $file = shift;
    my %coefs;
    
    # read in support vectors
    open( my $fh, '<', $file) or die "Can't open $file: $!";
    while ( <$fh> ) {
        chomp;
        my ($key, $val) = split;
        $coefs{$key} = $val;
    }
    return \%coefs;
}

# perform logistic regression
sub logreg {
    my ($featref, $modelref) = @_[0..1];
    my %features = % { $featref };
    $features{"(Intercept)"} = 1;
    my %coefs = % { $modelref };
    my $logit = 0;
    foreach my $key (keys %coefs) { 
        my $x =  $features{$key};
        $logit = $logit + $coefs{$key} * $features{$key};
    }
    return 1 / (1 + exp(-$logit));
}

1;

