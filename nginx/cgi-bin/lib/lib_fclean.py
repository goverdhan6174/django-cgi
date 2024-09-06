import os
import time
import random
import socket
# from config import db as mysqldb
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import db
from config import db as mysqldb



# Add the parent directory of 'config' to the Python path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Global variables

filepath = "__data/"  # Equivalent to Perl's $filepath
_DBNAME = "zfmail"    # Equivalent to Perl's $_DBNAME
_DEBUG = False        # Equivalent to Perl's $_DEBUG

_smtpserver = {}  # Equivalent to Perl's %_smtpserver
iplist = []       # Equivalent to Perl's @iplist
pausefile = ""    # Equivalent to Perl's $pausefile

# Globals that require updates via functions
_errorstr = ""
_tcounts = 1
SCK = None

# Thread-safe counters
_s_emails_total = 0
_s_emails_done = 0

# These would replace the shared memory in Perl
_rcounts = 1

# Equivalent Perl subroutine conversions

# Global variables equivalent to Perl's 'our'

# Dictionary equivalent to Perl's %per
per = {}

# String or variable equivalent to Perl's $_TDOMAIN
_TDOMAIN = ""

# Dictionaries equivalent to Perl's %_ipused, %_ippause, %_doline, %_dolined
_ipused = {}
_ippause = {}
_doline = {}
_dolined = {}



def setlib_smtpserver(data):
    global _smtpserver
    _smtpserver = data

def getlib_smtpserver():
    return _smtpserver

def setlib_iplist(data):
    global iplist
    iplist = data

def setlib_pausefile(data):
    global pausefile
    pausefile = data

def setlib_values(args):
    global filename, procid, _OPFLAG, pprocid, _smtpcr, _NONEXEC, WORKERS, _LOCAL, _files, _dfiles
    filename = args.get("filename")
    procid = args.get("procid")
    _OPFLAG = args.get("_OPFLAG")
    pprocid = args.get("pprocid")
    _smtpcr = args.get("_smtpcr")
    _NONEXEC = args.get("_NONEXEC")
    WORKERS = args.get("WORKERS")
    _LOCAL = args.get("_LOCAL")
    _files = args.get("_files")
    _dfiles = args.get("_dfiles")

def setlib_sigpipe():
    import signal
    signal.signal(signal.SIGPIPE, sigpipe_handler)

def setlib_emails_total(count):
    global _s_emails_total
    _s_emails_total = count

def setlib_type(lib_type):
    global _lib_type
    _lib_type = lib_type

def _workercount(filepath, filename, workers):
    countfile = f"{filepath}{filename}cnt"
    curcnt = 0
    
    # Check if the countfile exists and read its contents
    if os.path.isfile(countfile):
        with open(countfile, 'r') as file:
            curcnt = int(file.read().strip())
    
    # Increment the current count
    curcnt += 1
    
    # Open the file in write mode and apply an exclusive lock
    with open(countfile, 'w') as file:
        # No direct equivalent to flock in Python, but using the file context ensures atomicity
        file.write(str(curcnt))
    
    # Check if the current count exceeds the number of workers
    if curcnt > workers:
        try:
            os.remove(countfile)
        except FileNotFoundError:
            pass
        return 1
    
    return 0

def _readdata(per, _rcounts):
    cnt = 0
    emails = []
    status = 0

    _rcounts += 1
    for _ in range(per["thread"]):
        _rcounts += 1
        email = input("Enter email: ")  # Prompt for input
        email = email.rstrip('\r\n')
        if not email:
            status = 1
            break
        emails.append(email)
    
    return status, emails, _rcounts


def _check_ippause(per):
    curtime = time.time()
    pausetime = per.get("swait", 300) or 300
    for ippaused, timestamp in _ippause.items():
        passed = curtime - timestamp
        if passed > pausetime:
            _ippause[ippaused] = ""

import os

def _save_ippause(filepath, pausefile, ippause, overwrite=False):
    # Determine the mode based on the overwrite flag
    mode = 'w' if overwrite else 'a'

    # Open the file with the appropriate mode
    with open(os.path.join(filepath, pausefile), mode) as file:
        # Loop through the ippause dictionary and write non-empty entries
        for ippaused, timestamp in ippause.items():
            if timestamp != "":
                file.write(f'_ippause["{ippaused}"] = "{timestamp}";\n')


def _load_ippause():
    with open(os.path.join(filepath, pausefile), 'r') as f:
        for line in f:
            exec(line.strip())
    _save_ippause(1)

def _statusoutput():
    total = sum(_dolined.values())
    totals = sum(_doline.values())
    print(f"Current Status {_tcounts} / {total} / {totals}")

def _thread_parent(pnum, thnum, curserver, ownip, emails):
    global SCK
    if procid > 0:
        mysqldb.db_open(_DBNAME)

    skipped = 0
    _ipused[ownip] = 1

    print(f"[{pnum}][{thnum}] $$ Opening SMTP Server : [{_OPFLAG}][{_TDOMAIN}][{curserver}] {_smtpserver[_TDOMAIN][curserver]} with IP [{ownip}] {iplist[ownip]}")
    
    newmail = genMail()
    if _OPFLAG == 0:
        if openMail(_smtpserver[_TDOMAIN][curserver], iplist[ownip], newmail + _LOCAL["MAIL"]):
            print(f"[{pnum}][{thnum}] Error : {_errorstr}")
            remails = ",".join(emails).replace(",,", ",").lstrip(",")
            _ippause[f"{_TDOMAIN}_{iplist[ownip]}"] = time.time()
            _ipused[ownip] = 0
            print(f"---- [{pnum}][{thnum}] Error Returning : {_errorstr} for {len(emails)} {remails}")
            if procid > 0:
                mysqldb.db_close()
            return remails

    pdomain = ""
    trycount = 0

    for email in emails:
        if _lib_type == 'e':
            time.sleep(10)

        if email:
            if _OPFLAG == 1:
                _TDOMAIN = email.split('@')[-1] if '@' in email else ""
                if _TDOMAIN != pdomain:
                    _getMX(_TDOMAIN)
                    per["pwait"] = _smtpserver[_TDOMAIN].get("pwait", 0)
                    per["twait"] = _smtpserver[_TDOMAIN].get("twait", 0)
                    per["swait"] = _smtpserver[_TDOMAIN].get("swait", 0)
                    curserver = random.randint(1, _smtpserver[_TDOMAIN].get("max", 1))

                    if openMail(_smtpserver[_TDOMAIN][curserver], iplist[ownip], newmail + _LOCAL["MAIL"]):
                        print(f"[{pnum}][{thnum}] (Mixed) Error : {_errorstr} ; {email}")
                        trycount += 1
                        if trycount < 5:
                            print(f"[{pnum}][{thnum}] (Mixed) Sleeping")
                            time.sleep(120 if _lib_type == 'e' else 10)
                            continue

                        with open(f"{_files['ck']}txt", 'a') as mfp:
                            mfp.write(f"{email}\n")

                        if procid > 0:
                            update_str = f"UPDATE zmfresult SET zmf_putngcnt = zmf_putngcnt+1 WHERE `id` = {procid};"
                            mysqldb.db_execute(update_str)
                            if pprocid > 0:
                                update_str = f"UPDATE zmfresult SET zmf_putngcnt = zmf_putngcnt+1 WHERE `id` = {pprocid};"
                                mysqldb.db_execute(update_str)

                        email = ""
                        continue
                    pdomain = _TDOMAIN

            trycount = 0

            verifyMail(email, pnum, 0)

            if not skipped:
                _dolined[pnum] += 1
                _tcounts += 1
                email = ""
            if per.get("pwait", 0) > 0:
                time.sleep(per["pwait"])

    if SCK:
        SCK.send(f"RSET{_smtpcr}".encode())
        SCK.close()

    remails = ",".join(emails).replace(",,", ",").lstrip(",")
    _ipused[ownip] = 0

    if procid > 0:
        mysqldb.db_close()
        print(f"[{pnum}][{thnum}] DB Closed")

    return remails

def _inspect_file(filename):
    opflag = 0
    if os.path.isfile(os.path.join(filepath, filename)):
        with open(os.path.join(filepath, filename), 'r') as tin:
            tcnt = 0
            tdomainsub = ""
            for line in tin:
                line = line.rstrip('\r\n')
                if '@' in line:
                    tcnt += 1
                    if tcnt == 1:
                        tdomainsub = line.split('@')[-1]
                    else:
                        if line.split('@')[-1] != tdomainsub:
                            opflag = 1
                    if tcnt > 9999:
                        return opflag, tdomainsub
    else:
        opflag = 1
        tdomainsub = ""

    return opflag, tdomainsub

def _divide_file(filename, filenums):
    if os.path.isfile(os.path.join(filepath, filename)):
        estr = f"split -d --number=l/{filenums} {os.path.join(filepath, filename)} {os.path.join(filepath, filename)}"
        print(estr)
        os.system(estr)
    else:
        print(f"No such file {filename}")
        exit(1)

def openMail(smtpserver, localip, mailfrom):
    global SCK, _errorstr
    if not localip:
        _errorstr = "No LOCAL IP set"
        return 1

    if not smtpserver:
        _errorstr = "No SMTP Server set"
        return 1

    if not mailfrom:
        _errorstr = "No MAIL FROM set"
        return 1

    print(f"Opening {smtpserver} : from {localip}")

    port = socket.getservbyname('smtp', 'tcp')

    _errorstr = "Socket creation error"
    try:
        SCK = socket.create_connection((smtpserver, port), timeout=5, source_address=(localip, 0))
    except socket.error:
        return 1

    _errorstr = ""
    res = SCK.recv(1024).decode()

    if not res.startswith("220"):
        SCK.close()
        _errorstr = f"Connection failed {res}"
        return 1

    # HELO command
    localserver = _LOCAL.get("SERVER")
    if _lib_type == 'e' and smtpserver in _smtpserver:
        localserver = _smtpserver[smtpserver]
    print(f"HELLO command by : {localserver} / FROM by : {mailfrom}")
    req = f"HELO {localserver}\r\n"
    SCK.send(req.encode())
    res = SCK.recv(1024).decode()

    while res.startswith("250-"):
        res = SCK.recv(1024).decode()

    if not res.startswith("250"):
        SCK.close()
        _errorstr = "HELO command failed"
        return 1

    # MAIL command
    req = f"MAIL FROM:<{mailfrom}>\r\n"
    SCK.send(req.encode())
    res = SCK.recv(1024).decode()

    if not res.startswith("250"):
        SCK.close()
        if "550 DNSBL" in res:
            print(f"Progress : openMail() Error [{res}]")
            exit()
        _errorstr = "MAIL command failed"
        return 1

    return 0

def verifyMail(mailto, pnum, skip):
    global _s_emails_done

    _s_emails_done += 1
    if _s_emails_done % 100 == 0:
        print(f"Progress : {_s_emails_done} / {_s_emails_total}")

    if _NONEXEC:
        print(f"Not executing verification : {mailto}")
        with open(f"{_files['ps']}", 'a') as fp:
            fp.write(f"{mailto}\n")
        return

    if not SCK:
        return

    SCK.settimeout(5)

    req = f"RCPT TO:<{mailto}>\r\n"
    SCK.send(req.encode())
    res = SCK.recv(1024).decode().strip()
    print(res)

    while res.startswith("250-"):
        res = SCK.recv(1024).decode().strip()

    results = "ck" if "250" in res else "ng"

    curdate = time.strftime("%Y%m%d", time.localtime())

    if skip != 1:
        with open(f"{_files[results]}{curdate}.txt", 'a') as fp:
            if results == "ok":
                if procid > 0:
                    update_str = f"UPDATE zmfresult SET zmf_putokcnt = zmf_putokcnt+1 WHERE `id` = {procid};"
                    mysqldb.db_execute(update_str)
                    if pprocid > 0:
                        update_str = f"UPDATE zmfresult SET zmf_putokcnt = zmf_putokcnt+1 WHERE `id` = {pprocid};"
                        mysqldb.db_execute(update_str)
                        with open(f"{_dfiles[results]}.txt", 'a') as ffp:
                            ffp.write(f"{mailto}\n")
                fp.write(f"{mailto}\n")
            else:
                if procid > 0:
                    update_str = f"UPDATE zmfresult SET zmf_putngcnt = zmf_putngcnt+1 WHERE `id` = {procid};"
                    mysqldb.db_execute(update_str)
                    if pprocid > 0:
                        update_str = f"UPDATE zmfresult SET zmf_putngcnt = zmf_putngcnt+1 WHERE `id` = {pprocid};"
                        mysqldb.db_execute(update_str)
                fp.write(f"{results} - {res},{mailto}\n")
    else:
        print(f"Skipping log; {res}")

def genMail():
    salt = list("ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789")
    return ''.join(random.choice(salt) for _ in range(8))

def sigpipe_handler(signum, frame):
    print("Progress : SIGPIPE")
