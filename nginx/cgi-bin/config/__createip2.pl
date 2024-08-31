#!/usr/bin/perl

#$fromip = "80.208.192.1"; #4094
#$fromip = "195.181.224.1"; #4094
$fromip = "212.237.152.1"; #2048

$totalnum = 2046;

@fromips = split(/\./, $fromip);

for(my $loop1=1; $loop1<=$totalnum; $loop1++){
    print("\$iplist[$loop1] = \"".$fromips[0].".".$fromips[1].".".$fromips[2].".".$fromips[3]."\";\n");
    $fromips[3]++;
    if($fromips[3] > 255){
	$fromips[3] = 0;
	$fromips[2]++;
    }
}
