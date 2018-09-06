use strict;
use List::Util qw[min max];

# variant splice site is assumed to occur at the same AG or GT used by the wild-type splice site
sub check_for_denovo_donor {
	my ($tv, $vf, $allele, $cache) = @_[0..3];

    # intialize some variables
    my $tr = $tv->transcript;
    my $strand = $tr->strand();
    my $slice = $vf->feature_Slice();
    my ($ref, $alt) = split /\//, ($allele);
    my @null = (0, undef, undef, undef);
    return @null if $alt eq '*'; 

    # determine if valid candidate
    my @introns = @{ $tr->get_all_Introns };
    my @exons = @{ $tr->get_all_Exons };
    my $number = 0;
    if ($tv->exon_number) {
        ($number, my $number_of_exons) = split /\//, ($tv->exon_number);
        return 0 if ($number == $number_of_exons); # quit if final exon since there is no donor site
    } elsif ($tv->intron_number) {
        ($number, my $null) = split /\//, ($tv->intron_number);
    # edge-case: insertion occurring right at the splice junction
    } else {  
        $number = check_extended_splice_junctions_for_all_introns($tr, $slice, 1);
        return 0 if $number == -1;
    }

    # get relevant exon and intron
    my $intron = $introns[$number - 1];
    my $exon = $exons[$number - 1];
    my $exon_length = abs ($exon->{start} - $exon->{end}) + 1;

    # if only predicting exon truncation events, filter intronic variants that couldn't possibly create an exonic de novo site 
    if ($cache->{exonic_denovo_only}) {
        if ($strand == 1) {
            return @null if (($slice->{start} - 6) > $exon->{end});
        } else {
            return @null if (($slice->{end} + 6) < $exon->{start});
        }
    }

    # define boundaires of nucleotide sequence / filter variants occuring too far away from the splice junction
    my ($lb, $rb);
    my $max_dist = $cache->{max_denovo_donor_distance};
    if ($strand == 1) {
    	return @null if ($slice->{start} - $exon->{end}) > $max_dist || ($exon->{end} - $slice->{end}) > $max_dist;
        $lb = $exon->{start} - 200;
        $rb = $intron->{end} + 200;
	} else {
		return @null if ($exon->{start} - $slice->{end}) > $max_dist || ($slice->{start} - $exon->{start}) > $max_dist;
        $lb =  $intron->{start} - 200;
        $rb = $exon->{end} + 200;
	}
    # Note: sequence stretches from beginning of exon to end of intron, plus flanks

    # get wild-type nucleotide sequence
    my $left = $slice->{start} - $lb;
    my $right = $rb - $slice->{end};
    $slice->{strand} = 1; # weird hack, there must have been some reason this was neccessary ..
    my $wt_seq = uc($slice->expand($left, $right)->seq());

    # mutate wild-type nucleotide sequence to get variant nucleotide sequence
    my $upstream_flank = $left;
    if ($strand == -1) {
        $wt_seq = reverse_complement($wt_seq)->seq();
        $upstream_flank = $right;
    } 
    my ($var_seq, $nt_delta) = mutate_seq($wt_seq, $allele, $strand, $upstream_flank);

    # determine shift in location of authentic donor site
    my $exon_delta = (!$tv->intron_number) ? $nt_delta : 0; # remember we will never consider deletions affecting the essential splice site
    
    # locate landmarks in nucleotide sequence
    my $ref_junc = 200 + $exon_length + $exon_delta;
    my $var_pos = $upstream_flank; # position of variant in extracted nucleotide sequence

    # more filters
    my $ref = substr $var_seq, $ref_junc - 3, 9; # get consensus splice sequence at annotated junction
    #print "$ref\n";
    return @null if (length($ref) != 9 || $ref =~ /.*N.*/); # quit if MES score can't be computed 
    my $ref_mes = mes_donor_cache($cache, $ref);  
    
    # return if non-canonical donor site OR if reference site has very weak MES 
    return @null if ($ref_mes < $cache->{weak_donor_cutoff} || (substr $ref, 3, 2) ne "GT"); # model is completely reliant on MES for evaluating splice site strength, so a weak reference site results in an excess of de-novo predictions

    # initialize some variables for de novo splice site scan
    my $adj = ($nt_delta < 0)*-1 + ($nt_delta > 0)*($nt_delta - 1);
    my $flanksize = $cache->{sre_flanksize};
    my $best_prob = 0;
    my $best_mes_abs = -500;
    my ($best_delta, $best_mes_delta, %best_feats); # best_delta is the size of the resulting exon truncation/extension event (deletions are negative)
    my $motifs = $cache->{donor_motifs};

    # Scan for newly created splice sites
    for (my $pos=$var_pos - 8; $pos <= $var_pos + $adj; $pos++) {
        # get dimensions of putative new transcript
        my $new_junc = $pos + 3;
        my $intron_length = (length $var_seq) - 200 - $new_junc;
        my $current_exon_length = $new_junc - 200;
        my $delta = $new_junc - $ref_junc;

        # skip invalid candidates
        my $invalid = ($current_exon_length <= 0 || $new_junc == $ref_junc || $intron_length < 70);
        my $also_invalid = ($cache->{exonic_denovo_only} && $delta > 0);
        next if ($invalid || $also_invalid); 

        my $alt = substr $var_seq, $pos, 9;
        next if (length($alt) != 9 || $alt =~ /.*N.*/); # skip if MES can't be computed
        my $alt_mes = mes_donor_cache($cache, $alt);
        next if ($alt_mes - $ref_mes) < -15; # skip if candidate is clearly much weaker than reference

        # if you get here then you have a bona fide candidate ...
        
        # get upstream and downstream flanking sequence
        my ($up, $down) = sort ($ref_junc, $new_junc);
        my $lb = max($up - 3 - $flanksize, 0);
        my $upup = substr $var_seq, $lb, $up - 3 - $lb; # upstream flank of upstream splice site
        my $downup = substr $var_seq, $up + 6, $flanksize; # ditto
        my $lb = max($down - 3 - $flanksize, 0);
        my $updown = substr $var_seq, $lb, $down - 3 - $lb;
        my $downdown = substr $var_seq, $down + 6, $flanksize;

        # get features
        my %features = (
            "ese"  => scan_seq($motifs, $updown, 'ese') - scan_seq($motifs, $upup, 'ese'),
            "ess" => scan_seq($motifs, $updown, 'ess') - scan_seq($motifs, $upup, 'ess'),
            "ise" => scan_seq($motifs, $downdown, 'ise') - scan_seq($motifs, $downup, 'ise'),
            "iss" => scan_seq($motifs, $downdown, 'iss') - scan_seq($motifs, $downup, 'iss'),
            "MESdiff" => ($new_junc > $ref_junc) ? $alt_mes - $ref_mes : $ref_mes - $alt_mes
        );

        # compute SVM decision function
        my $marg = svm($cache->{donor_svm}, \%features, "radial");
        my $pr = svm_logreg($marg, $cache->{donor_svm});

        # evaluate
        $pr = 1 - $pr if $new_junc < $ref_junc;
        if ($pr > $best_prob) {
           $best_prob = $pr; 
           $best_delta = $delta;
           %best_feats = %features; 
        }
        if ($alt_mes > $best_mes_abs) {
           $best_mes_abs = $alt_mes;
           $best_mes_delta = $delta;
        }
    }

    my $lof = 0;
    # if in frame, determine if a stop codon has been introduced
    if (defined($best_delta) && (abs($best_delta) % 3) == 0) {
        my @stop_codons = ("TAG", "TAA", "TGA");
        my $best_junc = $ref_junc + $best_delta;
        my $consensus = substr $var_seq, $best_junc - 3, 9;

        # determine reading frame 
        my $cds_dist = get_cds_dist_to_exon($tr, $number - 1);
        my $leading_frame = (3 - ($cds_dist % 3)) % 3; # Number of bases to complete the final codon of the previous exon
        my $tailing_frame = ($exon_length - $leading_frame) % 3; # Number of bases to begin the first codon of the next exon
        
        # check the codon that spans the new junction (if there is none, this will be the first codon of the next exon)
        my $next_exon = $exons[$number];
        my $codon_completion = substr $next_exon->seq->seq(), 0, 3 - $tailing_frame;
        my $current_codon = (substr $var_seq, $best_junc - $tailing_frame, $tailing_frame) . $codon_completion;
        
        # check if a stop codon was introduced into extended exon sequence
        my $stop_introduced = 0;
        if ($best_junc > $ref_junc) {
            my $extension = substr $var_seq, $ref_junc - $tailing_frame, $best_delta;
            $stop_introduced = scan_for_stop_codons($extension);
        }
        $lof = $stop_introduced || $current_codon ~~ @stop_codons;
    # else, frameshift
    } else {
        $lof = 1;
    }

    # for debugging
    # foreach my $key ('ese', 'ess', 'ise', 'iss', 'MESdiff') {
    #     print $key . " : " . $best_feats{$key} . "\n";
    # }
    # print "$best_prob, $best_delta\n";
    # print "LoF? $lof\n";

    my %lof_info = (
        "DE_NOVO_DONOR_PROB" => $best_prob,
        "DE_NOVO_DONOR_POS" => $best_delta,
        "DE_NOVO_DONOR_MES" => $best_mes_abs,
        "DE_NOVO_DONOR_MES_POS" => $best_mes_delta,
        "MUTANT_DONOR_MES" => $ref_mes,
        "INTRON_START" => $intron->start,
        "INTRON_END" => $intron->end,
        "EXON_START" => $exon->start,
        "EXON_END" => $exon->end
        );

    my $lof_pos;
    if ($strand == 1) {
        $lof_pos = min($exon->end + $best_delta, $exon->end);
    } else {
        $lof_pos = max($exon->start - $best_delta, $exon->start);
    }
    return ($best_prob, \%lof_info, $lof, $lof_pos);
}

sub scan_for_stop_codons {
    my $seq = shift;
    my @stop_codons = ("TAG", "TAA", "TGA");
    for (my $pos=0; $pos < length($seq); $pos = $pos + 3) {
        my $codon = substr $seq, $pos, 3;
        return 1 if $codon ~~ @stop_codons;
    }
    return 0;
}


1;


