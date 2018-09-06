use strict;

sub get_gerp_weighted_dist {
    my ($tr, $pos, $gerp_db, $cons_db) = @_[0..3];

    # collect some variables
    my $chr = $tr->seq_region_name();
    my @exons = @{ $tr->get_all_Exons };
    my $strand = $tr->strand();
    my $transcript_id = $tr->{stable_id};
    my $number_of_exons = scalar @exons;

    # determine boundaries of CDS sequence
    my ($stop_codon_pos, $start_codon_pos);
    if ($strand == 1) {
        $stop_codon_pos = $tr->{coding_region_end};
        $start_codon_pos = $tr->{coding_region_start};
    } elsif ($strand == -1) {
        $stop_codon_pos = $tr->{coding_region_start};
        $start_codon_pos = $tr->{coding_region_end};
    }

    # get distance to from variant to stop codon, weighted by GERP
    my $weighted_dist = 0;
    my $dist = 0;
    for (my $i=0; $i <= $number_of_exons - 1; $i++) {
        my $current_exon = $exons[$i];
        # skip exons upstream of variant
        if ($strand == -1) {
            next if $pos < $current_exon->start;
        } else {
            next if $pos > $current_exon->end;
        }

        # determine if last exon by checking if exon spans stop codon position
        my $last_exon = 0;
        if ($strand == 1) {
            $last_exon = ($current_exon->start < $stop_codon_pos) && ($current_exon->end >= $stop_codon_pos);
        } else {
            $last_exon = ($current_exon->end > $stop_codon_pos) && ($current_exon->start <= $stop_codon_pos);
        }

        # get contribution of current exon to total weighted distance
        my ($start, $end, $wd);
        my $in_affected_exon = ($pos >= $current_exon->start) && ($pos <= $current_exon->end);
        if ($last_exon) {
            if ($in_affected_exon) {
                $start = $pos;
            } else {
                $start = ($strand == 1) ? $current_exon->start : $current_exon->end;
            }
            $end = $stop_codon_pos;
            $wd = get_interval_gerp($chr, $start, $end, $gerp_db);
        } elsif ($in_affected_exon) {
            $start = $pos;
            $end = ($strand == 1) ? $current_exon->{end} : $current_exon->{start};
            $wd = get_interval_gerp($chr, $start, $end, $gerp_db);
        } else {
            my $exon_num = $i + 1;
            $wd = get_exon_gerp($transcript_id, $exon_num, $cons_db);
            $start = $current_exon->start;
            $end = $current_exon->end;
        }
        $weighted_dist = $weighted_dist + $wd;
        $dist = $dist + (abs ($end - $start));
    }
    return ($weighted_dist, $dist);
}

sub get_interval_gerp {
    my ($chrom, $a, $b, $gerp_db) = @_[0..3];
    if ($gerp_db =~ 'tabix') {
        return (get_interval_gerp_tabix($chrom, $a, $b, $gerp_db));
    } else {
        return (get_interval_gerp_db($chrom, $a, $b, $gerp_db));
    }
}

sub get_interval_gerp_db {
    my ($chrom, $a, $b, $gerp_db) = @_[0..3];
    if ($a > $b) { my $tmp = $a; $a = $b; $b = $tmp; }
    my $sql_query = $gerp_db->prepare("SELECT sum(gerp) as gerp FROM gerp_bases where chrom = ? AND pos >= ? AND pos <= ?;");
    $sql_query->execute($chrom, $a, $b) or die("MySQL ERROR: $!");
    my $results = $sql_query->fetchrow_hashref;
    $sql_query->finish();
    return ($results->{gerp});
}

sub get_interval_gerp_tabix {
    my ($chrom, $a, $b, $gerp_db) = @_[0..3];
    if ($a > $b) { my $tmp = $a; $a = $b; $b = $tmp; }
    my @results = split /\n/, `$gerp_db $chrom:$a-$b 2>&1`;
    my $gerp = 0;
    for my $row (@results) {
        my @res = split /\t/, $row;
        $gerp += $res[2];
    }
    return ($gerp);
}

sub get_bp_gerp {
    my ($chrom, $pos, $gerp_db) = @_[0..3];
    if ($gerp_db =~ 'tabix') {
        return (get_bp_gerp_tabix($chrom, $pos, $gerp_db));
    } else {
        return (get_bp_gerp_db($chrom, $pos, $gerp_db));
    }
}
sub get_bp_gerp_db {
    my ($chrom, $pos, $gerp_db) = @_[0..2];
    my $sql_query = $gerp_db->prepare("SELECT * FROM gerp_bases where chrom = ? AND pos = ?;");
    $sql_query->execute($chrom, $pos) or die("MySQL ERROR: $!");
    my $results = $sql_query->fetchrow_hashref;
    $sql_query->finish();
    return ($results->{gerp});
}
sub get_bp_gerp_tabix {
    my ($chrom, $pos, $gerp_db) = @_[0..2];
    my $res = `$gerp_db $chrom:$pos-$pos 2>&1`;
    my @results = split /\t/, $res;
    return ($results[2]);
}


sub get_exon_gerp {
    my $transcript_id = shift;
    my $exon_number = shift;
    my $gerp_db = shift;
    my $sql_query = $gerp_db->prepare("SELECT * FROM gerp_exons where transcript_id = ? AND exon_num = ?; ");
    $sql_query->execute($transcript_id, $exon_number) or die("MySQL ERROR: $!");
    my $results = $sql_query->fetchrow_hashref;
    $sql_query->finish();
    return ($results->{gerp});
}

1;