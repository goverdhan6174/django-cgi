$_cgi{name} = "zfm.cgi";
$_cgi{url} = "zfm.cgi";
$_cgi{uploadurl} = "zfm.cgi";

#############################################
##
## 設定項目
## 

$_cgi{servername} = `hostname`;
if($_cgi{servername} =~ m/\./){
    $_cgi{servername} = $`; #`                                                                                                        
}
$_cgi{mode} = "indiv";

##
## 設定項目;end
##
#############################################

if($_LOCAL){
  $_cgi{exepath} = "http://localhost/zfm/";
}else{
   $_cgi{exepath} = "/zmf/";
}


sub url_encode($){
  my $str = shift;
  $str =~ s/([^\w ])/'%'.unpack('H2', $1)/eg;
  $str =~ tr/ /+/;
  return $str;
}

sub url_decode($){
  my $str = shift;
  $str =~ tr/+/ /;
  $str =~ s/%([0-9A-Fa-f][0-9A-Fa-f])/pack('H2', $1)/eg;
  return $str;
}

1;
