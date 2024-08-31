#!/usr/bin/perl
#################################################################################
##
## Fast Cleaner V3.0 
## 
## Mail Address Cleaner 
##
## Zexis S.ar.l  All Rights Reserved 2019 - 
## Nariaki HATTA ALL Rights Reserved 2019 -
##
## This Program is granted to use only by Zexis and Nariaki HATTA
##
##
use IO::Socket::INET;
use IO::Select;
use threads;
use threads::shared;
use Thread::Semaphore;
use Time::HiRes qw(usleep);

my $ipv = "r3";

require("./config/serverlist_new.pl");
require("./config/iplist_$ipv.pl");
#require("./config/db.cgi");
require("./config/_initial.pl");

if($_LOCAL){
    $_DBNAME = "zfmail";
}else{
    $_DBNAME = "zfmail";
}

$_NONEXEC = 0;

#$_LOCAL{SERVER} = "sociol.net";
#$_LOCAL{MAIL} = "\@sociol.net";
$_LOCAL{SERVER} = "yahoo.co.jp";
$_LOCAL{MAIL} = "\@yahoo.co.jp";
$_errorstr="";

$filepath = "__data/";
$filename = "emaildata_$ipv.txt";
$pausefile = "pause$ipv.txt";
$_tcounts = 0;

srand time;

$procid = $ARGV[1];
$pprocid = 0;
if($ARGV[3] ne ""){
  $pprocid = $ARGV[3];
} 

##
## File to be processed
if($ARGV[0] ne ""){
  print("fclean.exe @ARGV\n");

  my $_tmpfilename = $ARGV[0];
  print("TMPFILE : $filepath$_tmpfilename\n");
  if(! -f $filepath.$_tmpfilename){
    print("No File : $filepath$_tmpfilename Exists\n");
    &_statuslog()
  }else{
    $filename = $_tmpfilename;
  }
}

print("Processing file : $filename for $procid\n");

##
## Check PAUSED IPs
&_load_ippause();
&_check_ippause();
&_save_ippause();

##
## Default Values
$per{thread} = 7;              # Per thread email process number
$per{pwait} = 200 * 10;      # Per cleaning delay
$per{twait} = 200 * 10;      # Per thread delay
$per{swait} = 2*60;    # Per server change delay

my $WORKERS = 1;
my $THREADS = 5;
my $TOTALIP = $#iplist+1;
my $ENDWORKER = 0;

#$per{thread} = 1;      # Per thread email process number
#$WORKERS = 1;

##
## Shared variables for Threads
my %_ipused : shared = 1;
my %_ippause : shared = 1;
my %_doline : shared = 1;
my %_dolined : shared = 1;
my $_tcounts : shared = 1;
my $_rcounts : shared = 1;

my $endcount : shared = 1;

##
## Filename for File Output
##
$_files{ok} = $_files{ng} = $_files{ps} = $_files{ck} = $filepath."Result/".$filename;
if($ARGV[2] ne ""){
  print("Individual Saving $filename\n");
  $_dfiles{ok} = $_files{ng} = $_files{ps} = $_files{ck} = $filepath."Result/".$filename;
  $_dfiles{ok} =~ s/\.txt/\.ok\./;
  $_files{ok} = $filepath.$ARGV[2];
  $_files{ok} =~ m/(.+)\./;
  $_files{ok} = $1.".txt";
}

$_files{ok} =~ s/\.txt/\main.ok\./;
$_files{ng} =~ s/\.txt/\main.ng\./;
$_files{ps} =~ s/\.txt/\.ps\./;
$_files{ck} =~ s/\.txt/\.ck\./;

if($_files{ok} eq $_files{ng}){
  $_files{ok} = $_file.".ok.txt";
  $_files{ng} = $_file.".ng.txt";
}
print("Saving to  : $_dfiles{ok}  / $_files{ok}\n");

##
## STATUS File
## 
if($ipv eq ""){
    $ipv="auto";
}
$files{status} = "./STATUS/$ipv-";
my $delold = "/bin/rm $files{status}*";
print("Deletin OLD Status File; $files{status}\n");
`$delold`;

my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time());
$year += 1900;
$mon += 1;
$curdatestart = sprintf("%04d%02d%02d_%02d%02d", $year, $mon, $mday,$hour,$min );
$files{status} = "./STATUS/$ipv-start-$curdatestart";
`touch $files{status}`;

##
## Inspect File to Set Operation Mode
##
$__opflag[0] = "Specified Doomain Mode";
$__opflag[1] = "Mixed Doomain Mode";
($_OPFLAG, $_TDOMAIN) = &_inspect_file($filename);

$_TDOMAIN =~ s/[\r\n]//;

print("Operation Mode : $_OPFLAG $__opflag[$_OPFLAG] for $_TDOMAIN\n");

##
## Retrieve MX if Operation FLAG is "Specified Domain"
##

if($_OPFLAG eq 0){
  &_getMX($_TDOMAIN);
  $WORKERS = $_smtpserver{$_TDOMAIN}{max};
  if($_smtpserver{$_TDOMAIN}{thread} ne ""){
    $THREADS = $_smtpserver{$_TDOMAIN}{thread};
  }
  if($_smtpserver{$_TDOMAIN}{per} > 0){
    $per{thread} = $_smtpserver{$_TDOMAIN}{per};
    $per{pwait} = $_smtpserver{$_TDOMAIN}{pwait} * 10;
    $per{twait} = $_smtpserver{$_TDOMAIN}{twait} * 10;
    $per{swait} = $_smtpserver{$_TDOMAIN}{swait};
  }
  if($THREADS > $TOTALIP){
    $THREADS = $TOTALIP;
  }
}

if($THREAD eq ""){
  $THREADS = 1;
}

$THREADS = 80 ;

print("Number of WORKERS $WORKERS\n");
print("Number of Threads $THREADS\n");
print("Number of transaction / threads $per{thread}\n");
print("Delay times $per{pwait} / $per{twait} / $per{swait}\n");
print("Total IP Numbers $TOTALIP\n");

&_divide_file($filename, $WORKERS);

if($procid > 0){
  $_prg{starttime} = time();
  my $updatestr = "UPDATE zmfresult SET `zmf_from` = '$_prg{starttime}' WHERE `id` = $procid;";
  &mysqldb::db_open($_DBNAME);
  &mysqldb::db_execute($updatestr);
  &mysqldb::db_close();    
}

#$WORKERS = 1;

my @pids;
my $curpos = "";

$curserver = 0;
for(my $cloop=0; $cloop<$WORKERS; $cloop++){
  ##
  ## Access SMTP Server Selection
  $curserver++;
  print("[$curserver] MAX SMTP SERVER $_smtpserver{$_TDOMAIN}{max} \n");
  if($curserver > $_smtpserver{$_TDOMAIN}{max}){
    $curserver=1;
  }

  ##
  ## Fork Process
  my $pid = fork();
  if($pid){
    push(@pids, $pid);
    next;
  }else{
    my $openfile = sprintf("$filepath$filename%02d",$cloop);
    print("[$cloop] Child: $$ for $cloop : $openfile\n");
    print("[$cloop][$curserver] $$ Current SMTP Server : ".$_smtpserver{$_TDOMAIN}{$curserver}."\n");
    if(-f $openfile){
      ##
      ## For status, get number of data lines
      my $_cfilename = "/usr/bin/wc -l $openfile";
      my @_linecnt = split(/ /,`$_cfilename`);
      $_doline{$cloop} = $_linecnt[0];
      $_dolined{$cloop} = 0;

      open(FIN, $openfile);
      my $status = 0;
      while($status eq 0){
        my @thr;
	my $thloop, $thjloop;
	print("[$cloop] Status($status) Beginning THREAD \n");

	## Thread 
	for(my $thloop=0; $thloop<$THREADS; $thloop++){
          if($curpos[$thloop] ne ""){	    
	    print("[$cloop][$thloop] StoreVal_Begin($status) : $curpos[$thloop] \n");
	  }
	}

	##
	## Thread Loop
	##
        for($thloop=0; $thloop<$THREADS; $thloop++){
          my @_emails;
	  if($curpos[$thloop] =~ m/\@/){
	    $status = 0;
	    @_emails = split(/,/, $curpos[$thloop]);
	    print("[$cloop] Split [$thloop] $curpos[$thloop]\n");
	    $curpos[$thloop] = "";
	  }else{
	    ($status, @_emails) =  &_readdata();
	  }
	  ##
	  ## Obtaining Own IP
	  ##
	  $ownip = int(rand($TOTALIP));

	  ##
	  ## When it is "Specified Mode" we do not use same ip in threads
	  ##
	  if($_OPFLAG eq 0){
	    my $iploop=0;
	    while( $_ipused{$ownip} eq  1 || $_ippause{$_TDOMAIN."_".$iplist[$ownip]} ne ""){
	      $ownip = int(rand($TOTALIP));
	      $iploop++;
	      if($iploop>300){
		sleep(3);
		print("[$cloop] Checking IP Availabilities / $per{swait}\n");
		#
		# Will Check IP_Pause Status
		&_check_ippause();
		$iploop=0;
	      }
	    }
	    $_ipused{$ownip} = 1;
	  }else{
	    my $iploop=0;
	    while( $_ippause{$ownip} ne ""){
	      $ownip = int(rand($TOTALIP));
	      $iploop++;
	      if($iploop>300){
		sleep(3);
		print("[$cloop] Checking IP Availabilities / $per{swait}\n");
		#
		# Will Check IP_Pause Status
		&_check_ippause();
		$iploop=0;
	      }
	    }
	  }
          ($thr[$thloop]) = threads->new(\&_thread_parent, $cloop, $thloop, $curserver, $ownip, @_emails);
#	  $thr[$thloop] -> detach();
          print("[$cloop][$thloop] $$ Status : $status\n");
	  #
	  # When File END is reached
	  if($status eq 1 || $_dolined{$cloop} >= $_doline{$cloop} ){
            next;
#  	    $thloop++;
#	    last;
	  }
        }
	for($thjloop=0; $thjloop<$thloop; $thjloop++){
	  # When Error Occured while Verify Process, need to start from where it stopped
#          print("Waiting [$thjloop] $$ \n");
#          ($curpos[$thjloop], $_remails) = $thr[$thjloop] -> join();
          $curpos[$thjloop] = $thr[$thjloop] -> join();
	  if(length($curpos[$thjloop]) > 3){
	    print("[$cloop][$thjloop] Curpos : $curpos[$thjloop] \n");
	    $status = 0;
	  }
	}

	## TEST
#	for(my $thloop=0; $thloop<$THREADS; $thloop++){
#          if($curpos[$thloop] ne ""){	    
#	    print("[$cloop][$thloop] StoreVal($status) : $curpos[$thloop] \n");
#	    $status = 0;
#	  }
#	}

#	&_statusoutput();
	##
	## Thread Loop;End
	##
	if($per{twait}>0){
          print("- Waiting for Thread WAIT $per{twait}\n");
	  usleep($per{twait});
          print("- Waiting for Thread WAIT;End\n");	    
	}
      }
#      print("---- File END Exitted ?\n");
      close(FIN);
      ##
      ## Unlink Divided File after 1 second
      sleep(1);
      $endcount++;
      unlink($openfile);
    }
    last;
  }
}

print("---- Exitted ?\n");

##
## Wait for Forked Process to End
##
while(scalar(@pids)){
  my $child = shift(@pids);
  if (waitpid($child, WNOHANG)) {
      print "Finished: $child\n";
  }
  else {
      push(@pids, $child);
  }
}

##
## Save IP & SMTP Server Status
##
&_save_ippause();
print("Saving IPStatus : $endcount;\n");

##
## UPDATE Status
##
if($endcount eq 1){
    print("Updating Status to End\n");
    if($ipv eq ""){
	$ipv="auto";
    }
    $files{status} = "./STATUS/$ipv-";
    my $delold = "/bin/rm $files{status}*";
    `($delold) >& /dev/null`;
    my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time());
    $year += 1900;
    $mon += 1;
    $curdatestart = sprintf("%04d%02d%02d_%02d%02d", $year, $mon, $mday,$hour,$min );
    $files{status} = "./STATUS/$ipv-end-$curdatestart";
    `touch $files{status}`;
}

##
## Set processed data to "DONE"
##
if($procid > 0){
  if(&_workercount()){    
    print("[$ENDWORKDER] Setting Done mark to $procid\n");
    print("OK:$_files{ok}txt\n");
    print("NG:$_files{ng}txt\n");
    $_files{ok} =~ s/^$filepath//;
    $_files{ng} =~ s/^$filepath//;
    $_files{ck} =~ s/^$filepath//;
    
    $_prg{endtime} = time();
    my $updatestr = "UPDATE zmfresult SET `zmf_executed` = '-1', zmf_putokfile = '$_files{ok}txt', zmf_putngfile = '$_files{ng}txt', zmf_end ='$_prg{endtime}' WHERE `id` = $procid;";
    &mysqldb::db_open($_DBNAME);
    &mysqldb::db_execute($updatestr);
    &mysqldb::db_close();    
  }
}

##
## Delete Original File if it is SUB Process
##
if($pprocid > 0){
  if(-f $filepath.$_tmpfilename){
    unlink($filepath.$_tmpfilename);
  }
}

exit;

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
	      sleep(10);
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
      chomp($_);   	
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
  $req = "HELO $_LOCAL{SERVER}";
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
  $curdatestart = sprintf("%04d%02d%02d-$02d%02d", $year, $mon, $mday,$hour,$min );

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
