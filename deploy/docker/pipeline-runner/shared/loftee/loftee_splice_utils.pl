use strict;
use Bio::EnsEMBL::Variation::Utils::VariationEffect qw(overlap);

require "maxEntScan/score3.pl";
require "maxEntScan/score5.pl";

sub mes_donor_cache {
    my ($cache, $seq) = @_[0..1];
    if (exists($cache->{mes_donor_cache}{$seq})) {
    	my $score = $cache->{mes_donor_cache}{$seq};
    	return $score;
    } else {
    	my $score = mes_donor($cache, $seq);
    	$cache->{mes_donor_cache}{$seq} = $score;
    	return $score;
    }
}

sub mes_donor {
  my $cache = shift;
  my $str = shift;
  #print "$str\n";
  my %me2x5 = % { $cache->{me2x5} };
  my %seq = % { $cache->{seq} };
  return &log2(&score_consensus_donor($str)*$me2x5{$seq{&get_rest_donor($str)}});
}


sub mes_acceptor_cache {
	my ($cache, $seq) = @_[0..1];
    if (exists($cache->{mes_acceptor_cache}{$seq})) {
    	my $score = $cache->{mes_acceptor_cache}{$seq};
    	return $score;
    } else {
    	my $score = mes_acceptor($cache, $seq);
    	$cache->{mes_acceptor_cache}{$seq} = $score;
    	return $score;
    }
}


sub mes_acceptor {
  my $cache = shift;
  my $str = shift;
  return &log2(&score_consensus_acceptor($str)*&max_ent_score(&get_rest_acceptor($str),$cache->{metables}));
}


sub mutate_seq {
    my ($wtseq, $allele, $strand, $up_flank) = @_[0..3];
    my $varseq = ""; 
    my $nt_delta = 0;
    my ($ref, $alt) = split /\//, ($allele);
    my $start = ($up_flank > 0) * $up_flank;
    # insertion
    if ($ref eq "-") {
        $alt =  reverse_complement($alt)->seq() if ($strand == -1);
        $nt_delta = length $alt;
        $alt = substr $alt, ($up_flank < 0) * -$up_flank;
        $varseq = (substr $wtseq, 0, $start) . $alt . (substr $wtseq, $start);
    # deletion
    } elsif ($alt eq "-") {
        $varseq = (substr $wtseq, 0, $start) . (substr $wtseq, ($up_flank + length $ref));
        $nt_delta = (length $ref) * -1;
    # snp
    } else {
        $alt = reverse_complement($alt)->seq() if ($strand == -1);
        $varseq = (substr $wtseq, 0, $start) . $alt . (substr $wtseq, $start + 1);
    }
    return ($varseq, $nt_delta);
}

sub check_extended_splice_junctions_for_intron {
    my ($intron, $slice, $strand) = @_[0..2];
    my ($five_start, $five_end, $three_start, $three_end);
    if ($strand > 0) {
        ($five_start, $five_end) = ($intron->start - 3, $intron->start + 5);
        ($three_start, $three_end) = ($intron->end - 19, $intron->end + 3);
    } else {
        ($five_start, $five_end) = ($intron->end - 5, $intron->end + 3);
        ($three_start, $three_end) = ($intron->start - 3, $intron->start + 19);
    }
    if (overlap($slice->start, $slice->end, $five_start, $five_end)) {
        return (5, $five_start, $five_end);
    }
    if (overlap($slice->start, $slice->end, $three_start, $three_end)) {
        return (3, $three_start, $three_end);
    }
    return (0) x 3;
}


sub check_extended_splice_junctions_for_exon {
    my ($exon, $slice, $strand, $exon_num, $number_of_exons) = @_[0..4];
    my ($five_start, $five_end, $three_start, $three_end);
    if ($strand > 0) {
        ($five_start, $five_end) = ($exon->end - 2, $exon->end + 6);
        ($three_start, $three_end) = ($exon->start - 20, $exon->start + 2);
    } else {
        ($five_start, $five_end) = ($exon->start - 6, $exon->start + 2);
        ($three_start, $three_end) = ($exon->end - 2, $exon->end + 20);
    }
    if (overlap($slice->start, $slice->end, $five_start, $five_end) && $exon_num < $number_of_exons) {
        return (5, $five_start, $five_end);
    }
    if (overlap($slice->start, $slice->end, $three_start, $three_end) && $exon_num > 1) {
        return (3, $three_start, $three_end);
    }
    return (0) x 3;
}


sub check_extended_splice_junctions_for_all_introns {
    my ($tr, $slice, $get_idx) = @_[0..2];
    my $strand = $tr->strand();
    my $i = 0;
    foreach my $intron(@{$tr->get_all_Introns}) {
        my ($ss, $start, $end) = check_extended_splice_junctions_for_intron($intron, $slice, $strand);
        if ($ss != 0) {
            return ($get_idx) ? $i : ($intron, $i, $ss, $start, $end);
        }
        $i++;
    }
    return ($get_idx) ? -1 : (0) x 5;
}


sub check_if_extended_splice_variant {
    my ($tv, $slice) = @_[0..1];
    my $tr = $tv->transcript;
    my $strand = $tr->strand();
    if ($tv->intron_number) {
        my @introns = @{ $tr->get_all_Introns };
        my ($intron_num, $number_of_introns) = split /\//, ($tv->intron_number);
        my $intron = $introns[$intron_num - 1];
        my ($ss, $start, $end) = check_extended_splice_junctions_for_intron($intron, $slice, $strand);
        return ($intron, $intron_num - 1, $ss, $start, $end);
    } elsif ($tv->exon_number) {
        my @exons = @{ $tr->get_all_Exons };
        my ($exon_num, $number_of_exons) = split /\//, ($tv->exon_number);
        my $exon = $exons[$exon_num - 1];
        my @results = check_extended_splice_junctions_for_exon($exon, $slice, $strand, $exon_num, $number_of_exons);
        my ($ss, $start, $end) = @results;
        my $intron_idx = ($ss == 5) ? $exon_num - 1 : $exon_num - 2;
        my @introns = @{ $tr->get_all_Introns };
        return ($introns[$intron_idx], $intron_idx, $ss, $start, $end);
    } else {
        return check_extended_splice_junctions_for_all_introns($tr, $slice, 0);
    }
}

sub get_cds_dist_to_exon {
    my ($tr, $exon_idx) = @_[0..1];
    my @exons = @{ $tr->get_all_Exons };
    my $strand = $tr->strand();
    my $cds_start = ($strand == 1) ? $tr->{coding_region_start} : $tr->{coding_region_end};

    # determine length of CDS sequence up to the given exon
    my $dist_from_cds_start = 0;
    for (my $i=0; $i < $exon_idx; $i++) {
        my $ex = $exons[$i]; # current exon
        if ($strand == 1) {
            if ($cds_start > $ex->{end}) {
                next;
            } elsif ($cds_start > $ex->{start}) {
                $dist_from_cds_start = $dist_from_cds_start + $ex->{end} - $cds_start + 1;
            } else {
                $dist_from_cds_start = $dist_from_cds_start + $ex->{end} - $ex->{start} + 1;
            }
        } elsif ($strand == -1) {
            if ($cds_start < $ex->{start}) {
                next;
            } elsif ($cds_start < $ex->{end}) {
                $dist_from_cds_start = $dist_from_cds_start + $cds_start - $ex->{start} + 1;
            } else {
                $dist_from_cds_start = $dist_from_cds_start + $ex->{end} - $ex->{start} + 1; 
            }
        }
    }
    return $dist_from_cds_start;
}

sub scan_seq {
    my ($motifcacheref, $seq, $motif_type) = @_[0..2];
    my %motifcache = % { $motifcacheref };
    my @motifs = @ { $motifcache{$motif_type} };
    my %motif_hash = map { $_ => 1 } @motifs;
    my $l = scalar @motifs;
    my $n = length($seq);
    my $hits = 0;
    for (my $i=0; $i < $n; $i++) {
        my $kmer = substr $seq, $i, 6;
        $hits++ if exists($motif_hash{$kmer}) && length($kmer) == 6;
        my $kmer = substr $seq, $i, 7;
        last if (length($kmer) == 6);
        $hits++ if exists($motif_hash{$kmer}) && length($kmer) == 7;
        my $kmer = substr $seq, $i, 8;
        $hits++ if exists($motif_hash{$kmer}) && length($kmer) == 8;
    }
    return $hits;
}

sub get_motif_info {
    my $motif_dir = shift;
    my %motif_cache;

    # read in regulatory motif sequences
    my @motifs = ('ese', 'ess', 'ise', 'iss');
    foreach my $motif (@motifs) {
        my $file = catfile($motif_dir, $motif . '.txt');
        open ( my $handle, '<', $file ) or die "Can't open $file: $!";
        chomp ( my @lines = <$handle> );
        close $handle;
        $motif_cache{$motif} = \@lines;
    }
    return \%motif_cache;
}


sub read_file_into_2d_array {
    my $file = shift;
    open( my $fh, '<', $file) or die "Can't open $file: $!";
    my @array = ();
    while ( <$fh> ) {
        chomp;
        push @array, [ split ];
    }
    return \@array;
}

sub read_file_into_hash {
    my $file = shift;
    open( my $fh, '<', $file) or die "Can't open $file: $!";
    my %hash = ();
    while ( <$fh> ) {
        chomp;
        my ($key, $val) = split /\t/;
        $hash{$key} = $val;
    }
    return \%hash;
}

1;
