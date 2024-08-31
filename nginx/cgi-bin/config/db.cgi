package mysqldb;

use DBI;
use Encode qw(from_to);

##
## 
##
$_LOCAL = 0;
$_DEBUG = 0;  # デバッグモード:1 公開モード:0

##
## MySQL DB データ
## 
if($_LOCAL){
  $_db{user} = "root";
  $_db{pass} = "";
  $_db{host} = "localhost";
}else{
  $_db{user} = "root";
  $_db{pass} = "";
  $_db{host} = "localhost";
}

#########################################################################
##
## MySQL サブルーチン群 (MySQL DB内は UTF-8 で取り扱う）
##
# DB オープン
sub db_open()
{
  my $_dbname = $_[0];

  if($_dbname eq ""){
    return 1;
  }
  my $sleepcnt = 0;
  $_db{dsn} = "DBI:mysql:".$_dbname.";host=".$_db{host};
  $dbh = DBI->connect($_db{dsn}, $_db{user}, $_db{pass});
  while(!$dbh){
    sleep(1);
    $dbh = DBI->connect($_db{dsn}, $_db{user}, $_db{pass});
    $sleepcnt++;
    if($sleepcnt > 120){
      print("DB Access error <br>\n");
    }
  }
  $dbh->do("SET NAMES utf8;");
}

# DB クローズ
sub db_close()
{
  $dbh->disconnect;
}

# DB /
sub db_getlast()
{
}

# DB セレクト
sub db_select()
{
  my $_dbexestr = $_[0];
  my $_addwhere = $_[1];
  if($_addwhere){
    chop($_dbexestr);
    if($_dbexestr =~ m/where/ig){
      $_dbexestr = $`." where $_addwhere and $';";
    }else{
      if($_dbexestr =~ m/order by/ig){
        $_dbexestr = $`." where $_addwhere ORDER BY $';";
      }else{
        $_dbexestr .= " where".$_addwhere.";";
      }
    }
  }
  _print($_dbexestr);
  if( $_dbexestr_bkup eq $_dbexestr){
    _print("Same execution");
    return @_row;
  }
  @_row = ();
  $_dbexestr_bkup = $_dbexestr;
#  from_to($_dbexestr, 'shiftjis', 'utf8'); 
  $sth = $dbh->prepare($_dbexestr);
  $sth->execute;
  @_row=$sth->fetchrow_array;
  $sth->finish;
#  from_to(@_row, 'utf8', 'shiftjis'); 
  return @_row
}

# DB 行セレクト
sub db_select_row()
{
  my $_dbexestr = $_[0];
  my $_prefix = $_[1];
  my $_limit = $_[2];

#  $_DEBUG = 1; 

  if($_prefix eq "nowhere"){
    $_addwhere = "";
  }else{
    $_addwhere = $_prefix;
  }
  my @row, my $rcnt=0, my $_rtest;
  if($_addwhere){
#    chop($_dbexestr);
    if($_dbexestr =~ m/where/ig){
      $_dbexestr = $`." where ".$_addwhere." and $' $_limit;";
    }else{
      if($_dbexestr =~ m/order by/ig){
        $_dbexestr = $`." where ".$_addwhere." ORDER BY $' $_limit;";
      }else{
        $_dbexestr .= " where ".$_addwhere." $_limit;";
      }
    }
  }else{
    if($_dbexestr =~ m/\;$/){
      chop($_dbexestr);
    }
    $_dbexestr .= " ".$_limit.";";
  }

  _print($_dbexestr);
  if( $_dbexestr_bkup eq $_dbexestr){
    _print("Same execution");
    return @_row;
  }
  @_row = ();
  $_dbexestr_bkup = $_dbexestr;
#  from_to($_dbexestr, 'shiftjis', 'utf8'); 
  $sth = $dbh->prepare($_dbexestr);
  $sth->execute;
  while(@row = $sth->fetchrow_array){
    $_rtest = join(',',@row);
#    from_to($_rtest, 'utf8', 'shiftjis'); 
    $rcnt++;
    $_row[$rcnt] = $_rtest;
    _print($rcnt.":".$_rtest);
  }
  $sth->finish;
  return @_row;
}

# フォームから SQL 文を生成
# 引数(0) --> INSERT用
# 引数(1) --> UPDATE用
sub db_preparefromform()
{
   my $_editflag = $_[0];
   my $ccntt=1;
   my $_dbstrt = my $_dbstrh = "";
   while($form_type{$faction}[$ccntt] ne ""){
     $formname = "formv".$ccntt;
     if( $table_name{$faction}[$ccntt] ne "none"){
       if($_editflag){
         $_dbstrt .= " ".$table_name{$faction}[$ccntt]."='".$FORM{$formname}."',";
       }else{
         $_dbstrh .= $table_name{$faction}[$ccntt].",";
         $_dbstrt .= "'".$FORM{$formname}."',";
       }
     }
     $ccntt++;
   }
   
   chop($_dbstrh);
   chop($_dbstrt);
   
   if($_dbstrh ne ""){
     $_dbstrt = "( $_dbstrh ) VALUES ( $_dbstrt )";
   }
   return($_dbstrt);
}

# SQL の実行
sub db_execute()
{
#  use utf8;
  my $_dbexestr = $_[0];
#  utf8::decode($_dbexestr);
#  from_to($_dbexestr, 'shiftjis', 'utf8'); 
  $sth = $dbh->prepare($_dbexestr);
  return($sth->execute);
}

# 直前のＩＤの取得
sub db_get_lastid()
{
  $rv = $dbh->last_insert_id($_dbname,$_dbname,$_db{user},$_db{pass});
  return($rv);
}

##
##
#########################################################################

#########################################################################
##
## デバッグ用
##
sub _print()
{
 if($_DEBUG){
   $_cur = $_debug_cur;
   if($_[1] ne ""){
     $_cur = $_[1];
   }
   print("<FONT COLOR=red>[Debug][".$_cur."]</FONT> ".$_[0]."<BR>\n");
 }else{
 }
 return;
}

1;
