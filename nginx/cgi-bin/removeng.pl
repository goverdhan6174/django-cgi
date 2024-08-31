#!/usr/bin/perl
my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time());
$year += 1900;
$mon += 1;
$curdate = sprintf("%04d%02d%02d", $year, $mon, $mday );

$dir = '__data/Result';
opendir( $dh, $dir);

while (my $file = readdir $dh) {
    if($file =~ m/ng/ig){
	if($file =~ m/$curdate/ig){
	    # print "CUR : $file\n";	    
	}else{
	    my $unlink = "__data/Result/$file";
	    print "$unlink ";
	    if(-f $unlink){
		unlink($unlink);
		print " -- deleted \n";
	    }else{
		print " -- file error \n";
	    }
	}
    }else{
	# print "OK -- $file\n";
    }
}

closedir($dh);

