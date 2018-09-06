use strict;

my %bgd;
$bgd{'A'} = 0.27;
$bgd{'C'} = 0.23;
$bgd{'G'} = 0.23;
$bgd{'T'} = 0.27; 

my $read_from_file = (scalar @ARGV) > 0; 
my %me2x5;
my %seq;
if ($read_from_file) {
  my $inputfile = $ARGV[0];
  open (FILE,"<$inputfile") || die "can't open!\n";
  while(<FILE>) {
    chomp;
    if (/^\s*$/) { #discard blank lines;
      next;
    } 
    elsif (/^>/) { #discard comment lines;
      next;
    }
    else {
      $_ =~ s/\cM//g; #gets rid of carriage return
      my $str = $_;
      print $str."\t";
      $str = uc($str);
      print sprintf("%.2f",&log2(&score_consensus_donor($str)*$me2x5{$seq{&get_rest_donor($str)}}))."\n";
    }
  }
}



# Create a dictionary mapping sequence to its index within the 'splice5sequences' file. 
sub make_sequence_matrix {
  my $file = shift;
  my %matrix;
  my $n=0;
  open(SCOREF, $file) || die "Can't open $file!\n";
  while(<SCOREF>) { 
  	chomp;
  	$_=~ s/\s//; # remove any white space
  	$matrix{$_} = $n;
  	$n++;
  }
  close(SCOREF);
  return %matrix;
}

# Create a dictionary mapping sequence to score based on a given model. "
sub make_score_matrix{
  my $file = shift;
  my %matrix;
  my $n=0;
  open(SCOREF, $file) || die "Can't open $file!\n";
  while(<SCOREF>) { 
  	chomp;
  	$_=~ s/\s//;
  	$matrix{$n} = $_;
  	$n++;
  }
  close(SCOREF);
  return %matrix;
}

# Return sequence context minus the consensus part (i.e. the GT) 
sub get_rest_donor{
  my $seq = shift;
  my @seqa = split(//,uc($seq));
  return $seqa[0].$seqa[1].$seqa[2].$seqa[5].$seqa[6].$seqa[7].$seqa[8];
}

# Return a score for the likelihood of a consensus dinucleotide in a given sequence.  
sub score_consensus_donor {
  my $seq = shift; # candidate sequence to score
  my @seqa = split(//,uc($seq)); 
  my %bgd; # background frequency of nucleuotides
  $bgd{'A'} = 0.27; 
  $bgd{'C'} = 0.23; 
  $bgd{'G'} = 0.23; 
  $bgd{'T'} = 0.27;  
  my %cons1;
  $cons1{'A'} = 0.004;
  $cons1{'C'} = 0.0032;
  $cons1{'G'} = 0.9896;
  $cons1{'T'} = 0.0032;
  my %cons2;
  $cons2{'A'} = 0.0034; 
  $cons2{'C'} = 0.0039; 
  $cons2{'G'} = 0.0042; 
  $cons2{'T'} = 0.9884;
  my $addscore = $cons1{$seqa[3]}*$cons2{$seqa[4]}/($bgd{$seqa[3]}*$bgd{$seqa[4]}); # likelihood of given consensus sequence normalized by background likelihood 
  return $addscore;
}

sub log2{
  my ($val) = @_;
  return log($val)/log(2);
}

1;
