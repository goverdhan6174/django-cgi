#!/usr/bin/perl
#################################################################################
##
## Fast Cleaner V3.1 
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

my $ipv = "e1";
my $_VERSION = "3.1";

require("./config/serverlist_4096.pl");
require("./config/iplist_$ipv.pl");
#require("./config/db.cgi");
require("./config/_initial.pl");

# Added by H.Makino
require("./lib/lib_fclean.pl");
SETLIB_type('e');
&SETLIB_smtpserver(\%_smtpserver);
&SETLIB_iplist(\@iplist);

if($_LOCAL){
    $_DBNAME = "zfmail";
}else{
    $_DBNAME = "zfmail";
}

$_NONEXEC = 0;
##$_LOCAL{SERVER} = "yahoo.co.jp";
##$_LOCAL{MAIL} = "\@yahoo.co.jp";
$_LOCAL{SERVER} = "support-info.co.jp";
$_LOCAL{MAIL} = "\@support-info.co.jp";
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
    print("FCLEAN Ver $_VERSION\n");
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

# Added by H.Makino
&SETLIB_pausefile($pausefile);

##
## Check PAUSED IPs
&_load_ippause();
&_check_ippause();
&_save_ippause();

##
## Default Values
$per{thread} = 5;              # Per thread email process number
$per{pwait} = 200 * 10;      # Per cleaning delay
$per{twait} = 200 * 10;      # Per thread delay
$per{swait} = 2*60;    # Per server change delay # Seconds

my $WORKERS = 1;
my $THREADS = 5;
my $TOTALIP = $#iplist+1;
my $ENDWORKER = 0;

#$per{thread} = 1;      # Per thread email process number
#$WORKERS = 1;

##
## Shared variables for Threads
#=> Changed by Makino
#my %_ipused : shared = 1;
#my %_ippause : shared = 1;
#my %_doline : shared = 1;
#my %_dolined : shared = 1;
#<=> Changed by Makino
our %_ipused : shared = 1;
our %_ippause : shared = 1;
our %_doline : shared = 1;
our %_dolined : shared = 1;
#<= Changed by Makino
my $_tcounts : shared = 1;
# Removed by H.Makino
#my $_rcounts : shared = 1;

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

  # Added by H.Makino
  %_smtpserver = &GETLIB_smtpserver();

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

if($THREAD1 eq ""){
  $THREADS = 10;
}

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

# Added by H.Makino
my %args = (
  "filename" => $filename,
  "procid"   => $procid,
  "_OPFLAG"  => $_OPFLAG,
  "pprocid"  => $pprocid,
  "_smtpcr"  => $_smtpcr,
  "_NONEXEC" => $_NONEXEC,
  "WORKERS"  => $WORKERS,

  "_LOCAL"   => \%_LOCAL,
  "_files"   => \%_files,
  "_dfiles"  => \%_dfiles,
);
&SETLIB_values(\%args);

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
  ##----------------------------------------
  ## Added by H.Makino
  &SETLIB_sigpipe();
  ##----------------------------------------
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
      ##----------------------------------------
      ## Added by H.Makino
      &SETLIB_emails_total($_linecnt[0]);
      ##----------------------------------------
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
	      if($iploop>200){
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
	      if($iploop>200){
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

