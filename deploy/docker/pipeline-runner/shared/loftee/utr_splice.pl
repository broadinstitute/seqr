use strict;

sub check_5UTR {
    my ($transcript_variation, $variation_feature) = @_[0..1];
    #my $strand = $variation_feature->{strand};
    my $strand = $transcript_variation->transcript->strand;
    # Start is always less than or equal to end regardless of the orientation of the slice (true for introns as well).
    my $slice = $variation_feature->feature_Slice();

    # filter if variant occurs upstream of first intron
    if ($strand == 1) {
        my $cds_start = $transcript_variation->transcript->{coding_region_start};
        return ($slice->{end} < $cds_start);
    } elsif ($strand == -1) {
        my $cds_start = $transcript_variation->transcript->{coding_region_end};
        return ($slice->{start} > $cds_start);
    }
}

sub check_3UTR {
    my ($transcript_variation, $variation_feature) = @_[0..1];
    #my $strand = $variation_feature->{strand};
    my $strand = $transcript_variation->transcript->strand;
    # Start is always less than or equal to end regardless of the orientation of the slice (true for introns as well).
    my $slice = $variation_feature->feature_Slice();
    
    # filter if variant occurs downstream of last intron (i.e. not actually a splice donor site)
    if ($strand == 1) {
        my $cds_end = $transcript_variation->transcript->{coding_region_end};
        return ($slice->{start} > $cds_end);
    } elsif ($strand == -1) {
        my $cds_end = $transcript_variation->transcript->{coding_region_start};
        return ($slice->{end} < $cds_end);
    }
}

1;
