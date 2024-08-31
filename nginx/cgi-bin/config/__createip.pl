#!/usr/bin/perl

$fromip = "103.94.231.1";
$count="755";


@fromips = split(/\./, $fromip);

for(my $loop1=$fromips[3]; $loop1<=247; $loop1++){
    print("\$iplist[$count] = \"".$fromips[0].".".$fromips[1].".".$fromips[2].".".$loop1."\";\n");
    $count++;
}
