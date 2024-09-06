#########################################################################
## 2024/4/21 Set strict "vars" mode for check global
use strict "vars";

#------------------------------------------------------------------------
# Sets the Lexicant scope of subroutine local variables.
# This is not a good idea, but there's no need to edit existing code.

my $loop;		# _readdata()
my $_tdomainsub;	# _inspect_file()
my $port;		# openMail()
my $res;		# openMail(), verifyMail()
my $req;		# openMail(), verifyMail()
my $results;		# verifyMail()
my $curdate;		# verifyMail()
my @mxserver;		# _getMX()
my $_cur;		# _print()
my $cur;		# _print()

#------------------------------------------------------------------------
# Constant values.

my $filepath = "__data/";	# _workercount(), _save_ippause(), _load_ippause(), _inspect_file(), _divide_file()
my $_DBNAME = "zfmail";		# _thread_parent()
my $_DEBUG = 0;			#  _print()

#------------------------------------------------------------------------
# Settings only and no references, or only references and no settings.

my %_prg;		# verifyMail()
my $curdatestart;	# verifyMail()
my $_debug_cur;		# _print()

#------------------------------------------------------------------------
# Global scope variables in this file.

my $_errorstr="";
my $_tcounts : shared = 1;
my $SCK;

#------------------------------------------------------------------------
# Settings from main routine, not changed.

#== %_smtpserver
my %_smtpserver;
# Argument need to pass by reference.
sub SETLIB_smtpserver() {
  %_smtpserver = %{$_[0]};
}
sub GETLIB_smtpserver() {
  return(%_smtpserver);
}

#== @iplist
my @iplist;
# Argument need to pass by reference.
sub SETLIB_iplist() {
  @iplist = @{$_[0]};
}

#== $pausefile
my $pausefile;
sub SETLIB_pausefile() {
  $pausefile = $_[0];
}

#== $filename
#== $procid
#== $_OPFLAG
#== $pprocid
#== $_smtpcr
#== $_NONEXEC
#== $WORKERS
#== %_LOCAL
#== %_files
#== %_dfiles
my ($filename, $procid, $_OPFLAG, $pprocid, $_smtpcr, $_NONEXEC, $WORKERS);
my (%_LOCAL, %_files, %_dfiles);
# Argument need to pass by reference.
# Array element need to be reference.
sub SETLIB_values() {
  my $args  = $_[0];

  $filename = $$args{filename};
  $procid   = $$args{procid};
  $_OPFLAG  = $$args{_OPFLAG};
  $pprocid  = $$args{pprocid};
  $_smtpcr  = $$args{_smtpcr};
  $_NONEXEC = $$args{_NONEXEC};
  $WORKERS  = $$args{WORKERS};

  %_LOCAL   = %{$$args{_LOCAL}};
  %_files   = %{$$args{_files}};
  %_dfiles  = %{$$args{_dfiles}};
}

#------------------------------------------------------------------------
# Variables changed by each file.

our %per;
our $_TDOMAIN;
our %_ipused;
our %_ippause;
our %_doline;
our %_dolined;

#------------------------------------------------------------------------
# Additional Change

my $_s_emails_total : shared = 0;
my $_s_emails_done  : shared = 0;

# Set for SIGPIPE
sub SETLIB_sigpipe() {
  $SIG{PIPE} = \&_sigpipe;
}

# Set for $_s_emails_total
sub SETLIB_emails_total() {
  $_s_emails_total = $_[0];
}

# Set for __fclean_e*.cgi
my $_lib_type = '';
sub SETLIB_type() {
  $_lib_type = $_[0];
}

#########################################################################
##
##
##
sub _workercount(){
 my $countfile = $filepath.$filename."cnt";
 my $curcnt = 0;
 if(-f $countfile){
   $curcnt = `cat $countfile`;
 }
 $curcnt++;

 open(COUT, ">$countfile");
 flock(COUT, 2);
 print COUT $curcnt;
 close(COUT);
 
 if($curcnt > $WORKERS){
   unlink($countfile);
   return(1);
 }
 return(0); 
} 

#########################################################################
##
## Read per thread data from file specified in per{thead}
##

# Moved by H.Makino
my $_rcounts : shared = 1;

sub _readdata(){
  my $cnt = 0;
  my @_emails;
  my $status = 0;

  lock($_rcounts);
  for($loop=0; $loop< $per{thread}; $loop++){
    $_rcounts++;      
    $_emails[$loop] = readline FIN;
#    chomp($_emails[$loop]);
    $_emails[$loop] =~ s/[\r\n]+\z//;
    if(!defined($_emails[$loop])){
      $status = 1;
      last;
    }
  }
  return($status, @_emails);
}

#########################################################################
##
## Process IP Pause
##
## "Need to Consider PAUSE Seconds"
##
sub _check_ippause()
{

  my $curtime = time();
  my $pausetime = 30;
  if($per{swait} > 0){
    $pausetime = $per{swait};
  }else{
    $pausetime = 300;
  }
  foreach my $ippaused (keys %_ippause){
    my $passed = $curtime - $_ippause{$ippaused};
    if($passed >$pausetime){
      $_ippause{$ippaused} = ""; 
    }
  }
}

sub _save_ippause()
{
  my $_overwrite = $_[0];
  if( $_overwrite ){
    $_overwrite = ">";
  }else{
    $_overwrite = ">>";
  }
  open(POUT, $_overwrite.$filepath.$pausefile);
  flock(POUT, 2);
  foreach my $ippaused (keys %_ippause){
    if( $_ippause{$ippaused} ne "" ){
      print POUT "\$_ippause{\"$ippaused\"} = \"$_ippause{$ippaused}\";\n";
    }
  }
  close(POUT);
}

sub _load_ippause(){
  open(PIN, $filepath.$pausefile);
  while(<PIN>){
    eval($_);
  }
  close(PIN);
  &_save_ippause(1);
}

sub _statusoutput(){
  my $total = 0;
  my $totals = 0;
  foreach my $procnum (keys %_doline){
    $total += $_dolined{$procnum};
    $totals += $_doline{$procnum};  
  }
  print("Current Status $_tcounts / $total / $totals\n");
}

#########################################################################
##
## Parent of thread execution
##
sub _thread_parent()
{
  (my $pnum, my $thnum, my $curserver, my $ownip, my @_emails) = @_;
  if($procid > 0){
      &mysqldb::db_open($_DBNAME);
  }


  my $skipped = 0;
  $_ipused{$ownip} = 1;

  print("[$pnum][$thnum] $$ Opening SMTP Server : [$_OPFLAG][$_TDOMAIN][$curserver] ".$_smtpserver{$_TDOMAIN}{$curserver}." with IP [$ownip] $iplist[$ownip]\n");
  ##
  ## Connect To Mail Server
  ## 
  my $newmail = &genMail();
  if($_OPFLAG eq 0){
    if(openMail($_smtpserver{$_TDOMAIN}{$curserver}, $iplist[$ownip], $newmail.$_LOCAL{MAIL})){
      print("[$pnum][$thnum] Error : $_errorstr\n");
      my $_remails = join(",", @_emails);
      $_remails =~ s/\,+/\,/ig;
      $_remails =~ s/^,//;
      ##
      ## Sets IP PAUSE
      ##
      $_ippause{$_TDOMAIN."_".$iplist[$ownip]} = time();
      $_ipused{$ownip} = 0;
      print("---- [$pnum][$thnum] Error Returning : $_errorstr for $#_emails $_remails\n");
      if($procid > 0){
	&mysqldb::db_close();
      }
      threads->yield();
##      return($#_emails, $_remails);
      return($_remails);
    }
  }

  ##
  ## Process Mail Address Cleaning
  ##
  my $pdomain = "";
  my $_trycount = 0;

  for(my $loop=0; $loop<=$#_emails; $loop++){

# Merged by H.Makino
if ($_lib_type eq 'e') {
usleep(10000 * 1000);
}

    if($_emails[$loop] ne ""){
      if($_OPFLAG eq 1){
        $_TDOMAIN = "";
	if($_emails[$loop] =~ m/\@/){
	  $_TDOMAIN = $'; #'
	}
        if($_TDOMAIN ne $pdomain){
	  &_getMX($_TDOMAIN);
	  $per{pwait} = 0;
	  $per{twait} = 0;
	  $per{swait} = 0;
	  if($_smtpserver{$_TDOMAIN}{pwait} > 0){
	    $per{pwait} = $_smtpserver{$_TDOMAIN}{pwait};
	  }
	  if($_smtpserver{$_TDOMAIN}{twait} > 0){
	    $per{twait} = $_smtpserver{$_TDOMAIN}{twait};
	  }
	  if($_smtpserver{$_TDOMAIN}{swait} > 0){
	    $per{swait} = $_smtpserver{$_TDOMAIN}{swait};
	  }
	  $curserver = $_smtpserver{$_TDOMAIN}{max};
	  if($_smtpserver{$_TDOMAIN}{max}>1){
	    $curserver = int(rand($_smtpserver{$_TDOMAIN}{max}))+1;
	  }
	  if(openMail($_smtpserver{$_TDOMAIN}{$curserver}, $iplist[$ownip], $newmail.$_LOCAL{MAIL})){
	    print("[$pnum][$thnum] (Mixed) Error : $_errorstr ; $_emails[$loop]\n");
	    $_trycount++;
	    if($_trycount < 5){
              print("[$pnum][$thnum] (Mixed) Sleeping \n");		

	      # Merged by H.Makino
	      if ($_lib_type eq 'e') {
	      sleep(120);
	      } else {
	      sleep(10);
	      }

              $loop--;
	      next;
	    }
	    ##
	    ## Skipping by Connect Error
	    open(MFP, ">>".$_files{ck}."txt");
	    print MFP $_emails[$loop]."\n";
	    close(MFP);
	    if($procid > 0){
	      my $updatestr = "UPDATE zmfresult SET zmf_putngcnt = zmf_putngcnt+1 WHERE `id` = $procid;";
	      &mysqldb::db_execute($updatestr);
	      if($pprocid > 0){
	         my $updatestr = "UPDATE zmfresult SET zmf_putngcnt = zmf_putngcnt+1 WHERE `id` = $pprocid;";
		 &mysqldb::db_execute($updatestr);
	      }	  
	    }
	    $_emails[$loop] = "";
	    next;
	  }
	  $pdomain = $_TDOMAIN;
	}
      }

      $_trycount = 0;

      &verifyMail($_emails[$loop],$pnum,0);

      if(!$skipped){
        $_dolined{$pnum}++;
        $_tcounts++;
#        print("[$pnum][$thnum] Checked $_emails[$loop] $_dolined{$pnum} / $_doline{$pnum}\n");
	$_emails[$loop] = "";
      }else{
#	print("[$pnum][$thnum] Timeout Skipped $_emails[$loop] \n");
      }
      if($per{pwait}>0){
	usleep($per{pwait});
      }
    }
  }
  if($SCK){
    print $SCK "RSET$_smtpcr";
    $SCK->close;
  }

  my $_remails = join(",", @_emails);
  $_remails =~ s/\,+/\,/ig;
  $_remails =~ s/^\,//;

  threads->yield();
  $_ipused{$ownip} = 0;

  if($procid > 0){
      &mysqldb::db_close();
      print("[$pnum][$thnum] DB Closed\n");
  }

#  return($#_emails, $_remails);
  return($_remails);
}


#########################################################################
##
## Inspect File to set operation mode 
##
## "ONLY CHECKS FIRST 10,000 data !!!!!"
##
sub _inspect_file()
{
  my $filename = $_[0];
  my $opflag = 0;
  if( -f $filepath.$filename ){
    open(TIN, $filepath.$filename);
    my $tcnt = 0;
    while(<TIN>){
#      chomp($_);   	
      $_ =~ s/[\r\n]+\z//;
      if($_ =~ m/\@/){
        $tcnt++;
        if($tcnt eq 1){
	  $_tdomainsub = $'; #'
        }else{
          if( $' ne $_tdomainsub){ #'
	    $opflag = 1;  
          }
        }
#	print("$tcnt [$opflag]: $_\n");
	if($tcnt > 9999){
	  close(TIN);
	  return($opflag, $_tdomainsub);
	}
      }
    }
    close(TIN);
  }else{
    $opflag = 1;
    $_tdomainsub = "";
  }
  return($opflag, $_tdomainsub);
}

#########################################################################
##
## Divide file into specified number of files
##
sub _divide_file()
{
  my $filename = $_[0];
  my $filenums = $_[1];

  if( -f $filepath.$filename ){
    my $estr = "split -d --number=l/$filenums $filepath$filename $filepath$filename";
    print $estr."\n";
    `$estr`;
  }else{
    print("No such file $filename\n");
    exit(1);
  }
}

#########################################################################
##
## Mail Server Connection
##
## (smtp Server Address, MAIL from)
##
sub openMail()
{
  my $_smtpserver = $_[0];
  my $_localip = $_[1];
  my $_mailfrom = $_[2];
  
  if($_localip eq ""){
    $_errorstr = "No LOCAL IP set \n";
    return(1);
  }

  if($_smtpserver eq ""){
    $_errorstr = "No SMTP Server set \n";
    return(1);
  }

  if( $_mailfrom eq "" ){
    $_errorstr = "No MAIL FROM set\n";
    return(1);
  }

  print("Opening $_smtpserver : $port : from $_localip \n");

  ##
  ## Socket による接続
  ##
  my $port = getservbyname('smtp','tcp');

  $_errorstr = "Socket creation error";
  $SCK = IO::Socket::INET->new(
    PeerAddr => $_smtpserver,
    PeerPort => $port,
    Proto    => "tcp",
    LocalAddr => $_localip
#    LocalPort => 9001
    ) or return(1);

  my $timeo = pack("L!L!", 5, 0);
  $SCK->sockopt(SO_RCVTIMEO, $timeo);

  $_errorstr = "";
  select($SCK);
  $| = 1;
  select(STDOUT);
  $res = <$SCK>;
#  print($res);

  unless($res =~ /^220/){
    close($SCK);
    $_errorstr = "接続失敗 $res $!";
    return(1);
  }

  ##
  ## HELO コマンド発行
  ##

  # Merged by H.Makino
  if ($_lib_type eq 'e') {
  my $localserver = $_LOCAL{SERVER};
  if($_smtpserver{$_smtpserver} ne ""){
    $localserver = $_smtpserver{$_smtpserver};
  }
  print("HELLO command by : $localserver / FROM by : $_mailfrom\n");
  $req = "HELO $localserver";
  } else {
  $req = "HELO $_LOCAL{SERVER}";
  }

  print $SCK "$req$_smtpcr";

  $res = <$SCK>;
  $res =~ s/\x0D\x0A|\x0D|\x0A/\n/g;
  while($res =~ m/^\d{3}\-/){
    $res = <$SCK>;
    $res =~ s/\x0D\x0A|\x0D|\x0A/\n/g;
  }

  unless($res =~ /^2[2|5|0]0/){
    close($SCK);
    $_errorstr = "HELOコマンド失敗 $!";
    return(1);
  }

  ##
  ## MAIL コマンド発行
  ##
  $req = "MAIL FROM:<$_mailfrom>";
  print $SCK "$req$_smtpcr";
  $res = <$SCK>;
  $res =~ s/\x0D\x0A|\x0D|\x0A/\n/g;

  unless($res =~ /^2[2|5|0]0/){
    close($SCK);
    ##----------------------------------------
    ## Added 2023/10/21
    if($res =~ /^550 DNSBL/){
        print "Progress : openMail() Error [$res]\n";
        exit;
    }
    ##----------------------------------------
    $_errorstr = "MAILコマンド失敗 $!";
    return(1);
  }

  return(0);
}

#########################################################################
##
## Mail Address Cleaning Execution
##
## (MailAddress, File Output Flag)
##
sub verifyMail()
{
  my $_mailto = $_[0];  # Verify Addresses
  my $_pnum = $_[1];   # Process Number  
  my $_skip = $_[2];    # ファイル書出しフラグ（0;Write, 1:Skip)

  ##----------------------------------------
  ## Added 2023/10/21
  {
    lock($_s_emails_done);
    $_s_emails_done++;
    if (($_s_emails_done % 100) == 0) {
      print "Progress : $_s_emails_done / $_s_emails_total\n";
    }
  }
  ##----------------------------------------

#  $_skip = 1;

  ##
  ## DEBUG
##  open(FP, ">>TEST.$_pnum.txt");
##  $req = "RCPT TO:<$_mailto>";
##  print FP "$req\n";
##  close(FP);
  ##
  ##

  if($_NONEXEC){
    print("Not executing verification : $_mailto\n");
    open(FP, ">>".$_files{ps});
    print FP "$_mailto\n";    
    close(FP);
    return;
  }

  if(!$SCK){
    return;      
  }

#  my $timeo = pack("qq", 3, 0);
  my $timeo = pack("L!L!", 5, 0);
  $SCK->sockopt(SO_RCVTIMEO, $timeo);

  ##
  ## RCPT コマンド発行
  ##  
  $req = "RCPT TO:<$_mailto>";
  print $SCK "$req$_smtpcr";
  $res = <$SCK>;
  $res =~ s/\x0D\x0A|\x0D|\x0A/\n/g;
  chomp($res);
  print($res."\n");
  while($res =~ m/^\d{3}\-/){
    $res = <$SCK>;
    $res =~ s/\x0D\x0A|\x0D|\x0A/\n/g;
    chomp($res);
#    print($res."\n");
  }

  ##
  ## 結果判定
  ##
  $results = "ck";
  $results = "ng";
  if($res =~ m/2[25]0/){
    $results = "ok";
  }
  if($res =~ m/55[01234]/){
    $results = "ng";
  }

  ##
  ## v2 add Date
  $_prg{starttime} = time();
  my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time());
  $year += 1900;
  $mon += 1;
  $curdate = sprintf("%04d%02d%02d", $year, $mon, $mday );
  # $curdatestart = sprintf("%04d%02d%02d-$02d%02d", $year, $mon, $mday,$hour,$min );

  if($_skip ne 1){
#    open(FP, ">>".$_files{$results}."$_pnum.txt");
    open(FP, ">>".$_files{$results}."$curdate.txt");
    if($results eq "ok"){
      if($procid > 0){
	my $updatestr = "UPDATE zmfresult SET zmf_putokcnt = zmf_putokcnt+1 WHERE `id` = $procid;";
	&mysqldb::db_execute($updatestr);
        if($pprocid > 0){
  	  my $updatestr = "UPDATE zmfresult SET zmf_putokcnt = zmf_putokcnt+1 WHERE `id` = $pprocid;";
	  &mysqldb::db_execute($updatestr);
	  open(FFP, ">>".$_dfiles{$results}."txt");
	  print FFP "$_mailto\n";
	  close(FFP);
        }	  
      }
      print FP "$_mailto\n";
    }else{
      if($procid > 0){
	my $updatestr = "UPDATE zmfresult SET zmf_putngcnt = zmf_putngcnt+1 WHERE `id` = $procid;";
	&mysqldb::db_execute($updatestr);
        if($pprocid > 0){
	  my $updatestr = "UPDATE zmfresult SET zmf_putngcnt = zmf_putngcnt+1 WHERE `id` = $pprocid;";
	  &mysqldb::db_execute($updatestr);
        }	  
      }
      print FP $results." - ".$res.",$_mailto\n";
    }
    close(FP);
  }else{
    print("Skipping log; $res\n");
  }
}

#########################################################################
##
## Open Result Output Files
##
sub _openOutputFiles()
{
}

#########################################################################
##
## Mail Address Generation for "FROM"
##
sub genMail()
{
  my (@salt, $genemail);
  push @salt, 'A'..'H', 'J'..'N','P'..'Z';
  push @salt, 'a'..'k', 'm'..'z';
  push @salt, '2'..'9';

  for (1 .. 8){
    $genemail .= "$salt[int(rand($#salt+1))]";
  }
  return($genemail);
}


#########################################################################
##
## Status Out
##
sub _statuslog()
{
  my $statusfile = $_[0];
  my $statusstr = $_[1];
  my $statusnew= $_[2];

  my $_outstr = ">";
  if($statusnew eq 1){
    $_outstr = ">>";
  }

  open(STLOGOUT, $_outstr.$statusfile);
  print STLOGOUT $statusstr."\n";
  close(STLOGOUT);
}

#########################################################################
##
## Retrieve MX Records
##
sub _getMX()
{
  my $mxmail = $_[0]; 
  my $mxforce = $_[1];
  my $mxdomain = $mxmail;

  if( $mxmail =~ m/\@/ig){
    $mxdomain = $'; #';
  }
  print("Getting MX for $mxmail / $mxdomain\n");

  if($_smtpserver{$mxdomain}{mx} && $mxforce eq ""){
    print("Already have MX data\n");
    return(1);
  }

  my @mxresolve = split(/\n/, `dig mx $mxdomain +short`);

  if($mxresolve[0] eq ""){
    return(0);
  } 

  my $mxscnt = 0;
  my $mxserver;
  for(my $loop=0; $loop<=$#mxresolve; $loop++){
    $mxresolve[$loop] =~ m/ /g;
    $mxserver[$mxscnt] = $'; #'
    $mxscnt++;
  }

  ##
  ## Optain IP Address from MX Server Name  
  ## 
  my $mxcnt = 0;
  for(my $loop=0; $loop<$mxscnt; $loop++){
    @mxresolve = split(/\n/, `dig $mxserver[0] +short`);
    if($mxresolve[0] ne ""){
      for(my $mxloop=0; $mxloop<=$#mxresolve; $mxloop++){
	$mxcnt++; 
        $_smtpserver{$mxdomain}{$mxcnt} = $mxresolve[$mxloop];
#        print("[".$mxcnt."] [$mxdomain]- ".$mxresolve[$mxloop]."\n");
        print("[$mxcnt] $mxresolve[$mxloop]\n");
      }
    }
  }
  if($mxcnt ne 0){
    $_smtpserver{$mxdomain}{max} = $mxcnt;
    $_smtpserver{$mxdomain}{mx} = 1;
  }
  return(1);
}

#####################################################################
##
## デバッグ用
##
sub _print()
{
 if($_DEBUG){
   $_cur = $_debug_cur;
   if($_[1] ne ""){
     $_cur = "[".$_[1]."]";
   }
   print($cur.$_[0]);
 }
 return;
}

##----------------------------------------
## Added 2023/11/18
sub _sigpipe
{
  print("Progress : SIGPIPE\n");
}
##----------------------------------------

1;

