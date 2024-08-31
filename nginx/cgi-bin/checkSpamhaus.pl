#!/usr/bin/perl -s
#################################################################################
##
## Spamhaus 登録チェックプログラム
##
## IPアドレスのリストが Spamhaus に登録されているか確認する。
## -s -ipfile=<iplist ファイル名> で起動。
##
##

use Net::DNS;

#------------------------------
# DNS サーバ指定
# デフォルトの DNS サーバでチェックできない時に使用
$NAME_SERVER = '208.67.222.222';    # OpenDNS Home

#------------------------------
# パラメータチェック

print "-ipfile=<iplistファイル名> を指定して下さい\n" and exit if (!$ipfile);
print "$ipfile ファイルが存在しません\n" and exit if (! -f $ipfile);

#------------------------------
# ipfile 読み込み

#require("./config/iplist.80.pl");
#require("./config/iplist.195.pl");
#require("./config/iplist.212.pl");

require($ipfile);

#------------------------------

# パイプでつないだ場合のバッファリングを無くす
$|=1;

# Net::DNS で persistent_udp(1) で接続する場合
&_checkSpamhaus_NetDNS(\@iplist);

exit;


#########################################################################
##
## Check Spamhaus Registration
##

sub _checkSpamhaus_NetDNS() {
  my @iplist = @{@_[0]};

# For test data
#  @iplist = ('183.79.250.251');

  if ($NAME_SERVER) {
    $resolver = Net::DNS::Resolver->new( nameservers => [ $NAME_SERVER ] );
  } else {
    $resolver = Net::DNS::Resolver->new;
  }

  # persistent_tcp(1) を指定しても TCP 接続にならなかった。
#  $resolver->persistent_tcp(1);
  $resolver->persistent_udp(1);

  my $cnt_ok = 0;
  my $cnt_ng = 0;
  foreach my $ipaddr (@iplist) {
    if (!$ipaddr) {
      next;
    }

# for debug
#    print("------------------------------\n");
#    print("$ipaddr : ");

    # Spamhaus で 80.208.192.1 の登録を調べる場合
    # => 1.192.208.80.zen.spamhaus.org

    @digit = split(/\./, $ipaddr);
    $query = "$digit[3].$digit[2].$digit[1].$digit[0].zen.spamhaus.org";

    # DNS にクエリ
    $record = $resolver->search($query);

    if ($record) {
      # 登録あり
      $cnt_ng++;
      print('$iplist_ng[' . $cnt_ng . '] = "' . $ipaddr . '";    # NG' . "\n");

# for debug
#      print("NG\n");
#      foreach $rr ($record->answer) {
#        print( $rr->type . ' ' . $rr->address . "\n");
#      }

    } else {
      # 登録無し
      $cnt_ok++;
      print('$iplist[' . $cnt_ok . '] = "' . $ipaddr . '";    # OK' . "\n");

# for debug
#      print("OK\n");
#      print( 'ErrorString : ' . $res->errorstring . "\n");

    }
  }
}

#########################################################################

