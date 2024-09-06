import os
import sys
import time
import threading
import random
import subprocess
from filelock import FileLock
import dns.resolver
import dns.name
import sqlite3
from filelock import FileLock
import socket

import string
import dns.resolver


# comment out _ippause below
# renamed _get_mx fn To _getMX and moved fn to top
# Goverdhan's changes
from collections import defaultdict
_ippause = defaultdict(int)
_prg = {}


# Setting the transmission type
ipv = "d3"


pids = []
curpos = []
endcount = 0
curserver = 0

# Import configuration files safely
import config.serverlist_4096 as serverlist
import config.iplist_d1 as iplist  # Replace with f'config.iplist_{ipv}' if needed
import config._initial as initial
import config.db as mysqldb


# Local settings
_LOCAL = {
    'DBNAME': 'zfmail',
    'SERVER': 'support-info.co.jp',
    'MAIL': '@support-info.co.jp'
}

DBNAME = _LOCAL.get('DBNAME', 'default_db')

# Default values
per = {
    'thread': 5,
    'pwait': 2000,
    'twait': 2000,
    'swait': 120
}

WORKERS = 1
THREADS = 5
TOTALIP = len(iplist.iplist)
ENDWORKER = 0

# Shared variables for threads
_ipused = threading.Lock()
# _ippause = threading.Lock()
_doline = threading.Lock()
_dolined = threading.Lock()
_tcounts = threading.Lock()
_rcounts = threading.Lock()

endcount = threading.Lock()
_errorstr = ""

filepath = "__data/"
filename = f"emaildata_{ipv}.txt"
pausefile = f"pause{ipv}.txt"

random.seed(time.time())

# Ensure that the correct number of command-line arguments are provided
if len(sys.argv) < 2:
    print("Usage: python __fclean_d1.py <procid> [pprocid]")
    sys.exit(1)

procid = sys.argv[1]
pprocid = sys.argv[2] if len(sys.argv) > 2 else 0

#### STATUSLOG ####
def _statuslog(statusfile, statusstr, statusnew):
    mode = 'w' if statusnew == 0 else 'a'
    with open(statusfile, mode) as f:
        f.write(statusstr + "\n")

# Process file handling
if sys.argv[0]:
    print(f"fclean.exe {' '.join(sys.argv)}")

    _tmpfilename = sys.argv[0]
    print(f"TMPFILE : {os.path.join(filepath, _tmpfilename)}")
    if not os.path.isfile(os.path.join(filepath, _tmpfilename)):
        print(f"No File : {os.path.join(filepath, _tmpfilename)} Exists")
        _statuslog('status.log', f"No File : {os.path.join(filepath, _tmpfilename)} Exists", 1)
    else:
        filename = _tmpfilename

######
start_time = time.time()
print(f"Start time: {start_time}")
######

print(f"Processing file : {filename} for {procid}")

#########################################################################
## Process IP Pause
## "Need to Consider PAUSE Seconds"
def _check_ippause_external(_ippause, per_swait):
    curtime = time.time()
    pausetime = max(per_swait, 30) if per_swait > 0 else 300

    for ippaused in list(_ippause.keys()):
        if curtime - _ippause[ippaused] > pausetime:
            _ippause[ippaused] = None  # Equivalent to empty string in Perl

def _save_ippause(ippause, filepath, pausefile, overwrite=False):
    mode = 'w' if overwrite else 'a'
    with open(os.path.join(filepath, pausefile), mode) as pout:
        for ippaused, timestamp in ippause.items():
            if timestamp is not None:
                pout.write(f'ippause["{ippaused}"] = "{timestamp}";\n')

def _load_ippause(filepath, pausefile):
    full_path = os.path.join(filepath, pausefile)
    if os.path.isfile(full_path):
        with open(full_path, 'r') as f:
            paused_ips = f.read().splitlines()
            print("Paused IPs loaded:", paused_ips)
    else:
        print("Pause file does not exist")

def _statusoutput(doline, tcounts):
    total = sum(doline.values())
    print(f"Current Status {tcounts} / {total} / {total}")


def _inspect_file(filename):
    """
    Inspect File to set operation mode
    "ONLY CHECKS FIRST 10,000 data !!!!!"
    """
    opflag = 0
    tdomainsub = ""

    file_path = filepath + filename
    if os.path.isfile(file_path):
        try:
            with open(file_path, 'r') as tin:
                tcnt = 0
                for line in tin:
                    line = line.strip()
                    if "@" in line:
                        tcnt += 1
                        if tcnt == 1:
                            tdomainsub = line.split('@')[1]
                        else:
                            if line.split('@')[1] != tdomainsub:
                                opflag = 1
                        if tcnt > 9999:
                            return opflag, tdomainsub
        except OSError as e:
            print(f"Error reading file {file_path}: {e}")
            opflag = 1
            tdomainsub = ""
    else:
        opflag = 1
        tdomainsub = ""

    return opflag, tdomainsub


# Function to divide a file into the specified number of files
def _divide_file(filename, filenums):
    """
    Divide file into specified number of files
    """
    file_path = filepath + filename
    
    if os.path.isfile(file_path):
        estr = f"split -d --number=l/{filenums} {file_path} {file_path}"
        print(estr)
        try:
            subprocess.run(estr, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error during file split: {e}")
            raise
    else:
        print(f"No such file {filename}")
        raise FileNotFoundError(f"No such file: {filename}")

def send_command(sock, command):
    """
    Sends a command to the SMTP server and reads the response.

    :param sock: The socket object to use for communication.
    :param command: The command to send to the server.
    :return: The response from the server.
    """
    try:
        sock.sendall((command + "\r\n").encode('utf-8'))
        response = sock.recv(1024).decode('utf-8')
        # Normalize line endings
        response = response.replace('\r\n', '\n').replace('\r', '\n')
        return response
    except socket.error as e:
        print(f"Error sending command {command}: {e}")
        raise

def open_mail(smtp_server, local_ip, mail_from):
    """
    Connects to the SMTP server, sends HELO and MAIL commands, and checks the responses.

    :param smtp_server: The SMTP server address.
    :param local_ip: The local IP address to bind.
    :param mail_from: The MAIL FROM address.
    :return: 0 if successful, 1 if there was an error.
    """
    global error_str

    if not local_ip:
        error_str = "No LOCAL IP set"
        return 1

    if not smtp_server:
        error_str = "No SMTP Server set"
        return 1

    if not mail_from:
        error_str = "No MAIL FROM set"
        return 1

    print(f"Opening {smtp_server} : port : from {local_ip}")

    try:
        # Resolve SMTP port (usually 25, but can vary)
        port = socket.getservbyname('smtp', 'tcp')
        
        # Create and configure the socket
        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sck.settimeout(5)  # Set timeout for socket operations
        sck.bind((local_ip, 0))  # Bind to an available port
        sck.connect((smtp_server, port))
        
        # Send HELO command
        helo_command = f"HELO {local_ip}"  # Use local IP or server name as needed
        response = send_command(sck, helo_command)
        
        # Check for continuation responses
        while response.startswith(('4', '5')):
            response = send_command(sck, "")
        
        if not response.startswith(('220', '250')):
            sck.close()
            error_str = f"HELO command failed: {response}"
            return 1

        # Send MAIL FROM command
        mail_from_command = f"MAIL FROM:<{mail_from}>"
        response = send_command(sck, mail_from_command)

        if not response.startswith(('220', '250')):
            sck.close()
            error_str = f"MAIL command failed: {response}"
            return 1

        return 0

    except Exception as e:
        error_str = f"Socket creation error: {e}"
        return 1

def verify_mail(mailto, pnum, skip):
    """
    Verify an email address using the RCPT TO command.

    :param mailto: The email address to verify.
    :param pnum: The process number (for debugging/logging).
    :param skip: Flag indicating whether to skip file output (0: Write, 1: Skip).
    """
    global SCK, error_str, files, NONEXEC

    if NONEXEC:
        print(f"Not executing verification: {mailto}")
        with open(files['ps'], "a") as fp:
            fp.write(f"{mailto}\n")
        return

    if not SCK:
        print("Socket not initialized.")
        return

    # Set socket timeout
    timeout = 5  # Timeout in seconds
    SCK.settimeout(timeout)

    # Send RCPT TO command
    req = f"RCPT TO:<{mailto}>"
    send_command(SCK, req)
    response = receive_response(SCK)

    print(response)

    # Handle multi-line response
    while response.startswith(('4', '5')):
        response = receive_response(SCK)
        print(response)

def send_command(sock, command):
    """
    Sends a command to the SMTP server.

    :param sock: The socket object to use for communication.
    :param command: The command to send.
    """
    try:
        sock.sendall((command + "\r\n").encode('utf-8'))
    except socket.error as e:
        print(f"Error sending command {command}: {e}")

def receive_response(sock):
    """
    Receives a response from the SMTP server.

    :param sock: The socket object to use for communication.
    :return: The response from the server.
    """
    try:
        response = sock.recv(1024).decode('utf-8')
        # Normalize line endings
        response = response.replace('\r\n', '\n').replace('\r', '\n')
        return response.strip()
    except socket.error as e:
        print(f"Error receiving response: {e}")
        return ""

def log_results(sck, mailto, skip, procid, pprocid, files, db_conn):
    """
    Logs the result of email verification and updates the database.

    :param sck: The socket object used for communication.
    :param mailto: The email address that was verified.
    :param skip: Flag indicating whether to skip file output (0: Write, 1: Skip).
    :param procid: Process ID for database updates.
    :param pprocid: Parent process ID for database updates.
    :param files: Dictionary of file paths for logging results.
    :param db_conn: SQLite connection object for database operations.
    """
    # Determine result based on response
    response = sck.recv(1024).decode('utf-8').strip()  # Assuming `sck` is used for receiving response
    results = "ck"
    if "250" in response:
        results = "ok"
    elif any(code in response for code in ("550", "551", "552", "553", "554")):
        results = "ng"

    # Add date and time
    start_time = time.time()
    cur_time = time.localtime(start_time)
    cur_date = time.strftime("%Y%m%d", cur_time)
    cur_date_start = time.strftime("%Y%m%d-%H%M", cur_time)

    if skip != 1:
        log_file = f"{files[results]}{cur_date}.txt"
        with open(log_file, "a") as fp:
            if results == "ok":
                if procid > 0:
                    update_database(db_conn, procid, 'zmf_putokcnt', 1)
                    if pprocid > 0:
                        update_database(db_conn, pprocid, 'zmf_putokcnt', 1)
                        with open(f"{files['dfiles'][results]}txt", "a") as ffp:
                            ffp.write(f"{mailto}\n")
            else:
                if procid > 0:
                    update_database(db_conn, procid, 'zmf_putngcnt', 1)
                    if pprocid > 0:
                        update_database(db_conn, pprocid, 'zmf_putngcnt', 1)
                fp.write(f"{results} - {response}, {mailto}\n")
    else:
        print(f"Skipping log; {response}")

def update_database(db_conn, record_id, column, increment):
    """
    Updates the count in the database.

    :param db_conn: SQLite connection object.
    :param record_id: ID of the record to update.
    :param column: Column to increment.
    :param increment: Value to increment by.
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(f"UPDATE zmfresult SET {column} = {column} + ? WHERE id = ?", (increment, record_id))
        db_conn.commit()
    except Exception as e:
        print(f"Database update error: {e}")

def open_output_files():
    """
    Placeholder function for opening output files.
    Implement as needed based on your file handling requirements.
    """
    pass

def gen_mail():
    """
    Generates a random email address prefix using a specified set of characters.
    
    :return: A random email address prefix.
    """
    salt = (
        string.ascii_uppercase[:8] + string.ascii_uppercase[9:14] + 
        string.ascii_uppercase[15:] + 
        string.ascii_lowercase[:11] + string.ascii_lowercase[12:] + 
        '23456789'
    )
    genemail = ''.join(random.choice(salt) for _ in range(8))
    return genemail

def status_log(status_file, status_str, status_new):
    """
    Logs status messages to a file.

    :param status_file: The path to the status file.
    :param status_str: The status message to log.
    :param status_new: Flag indicating whether to overwrite (1) or append (0).
    """
    mode = 'w' if status_new == 1 else 'a'
    with open(status_file, mode) as st_log_out:
        st_log_out.write(status_str + "\n")

def _getMX(mxmail, mxforce):
    """
    Retrieves MX records for a given domain.

    :param mxmail: The email address or domain to retrieve MX records for.
    :param mxforce: Flag to force retrieval even if MX records are cached.
    :return: 1 if MX records are successfully retrieved, 0 otherwise.
    """
    # Extract domain from email address if present
    if '@' in mxmail:
        mxdomain = mxmail.split('@')[1]
    else:
        mxdomain = mxmail

    print(f"Getting MX for {mxmail} / {mxdomain}")

    # Check if MX records are already cached
    if mxdomain in smtpserver and 'mx' in smtpserver[mxdomain] and not mxforce:
        print("Already have MX data")
        return 1

    try:
        # Retrieve MX records
        mx_records = dns.resolver.resolve(mxdomain, 'MX')
        mx_servers = [str(record.exchange).rstrip('.') for record in mx_records]
        
        if not mx_servers:
            return 0

        mx_count = 0
        smtpserver[mxdomain] = {'mx': 1}  # Initialize entry
        for mx_server in mx_servers:
            try:
                # Retrieve A records for MX servers
                a_records = dns.resolver.resolve(mx_server, 'A')
                for a_record in a_records:
                    mx_count += 1
                    if mxdomain not in smtpserver:
                        smtpserver[mxdomain] = {}
                    smtpserver[mxdomain][mx_count] = str(a_record.address)
                    print(f"[{mx_count}] {a_record.address}")
            except dns.resolver.NoAnswer:
                print(f"No A record found for MX server {mx_server}")
            except dns.resolver.NXDOMAIN:
                print(f"MX server {mx_server} does not exist")

        if mx_count != 0:
            smtpserver[mxdomain]['max'] = mx_count
        
        return 1
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN) as e:
        print(f"Error retrieving MX records: {e}")
        return 0

# Load and check paused IPs
_load_ippause(filepath, pausefile)
_check_ippause_external(_ippause, per['swait'])
_save_ippause(_ippause, filepath, pausefile)

# Filename for File Output
files = {}
dfiles = {}

result_path = os.path.join(filepath, "Result")
files['ok'] = files['ng'] = files['ps'] = files['ck'] = os.path.join(result_path, filename)

if len(sys.argv) > 2 and sys.argv[2]:
    print(f"Individual Saving {filename}")
    dfiles['ok'] = os.path.join(result_path, filename).replace(".txt", ".ok.")
    files['ok'] = os.path.join(filepath, sys.argv[2])
    files['ok'] = re.sub(r"(.+)\.", r"\1.txt", files['ok'])

files['ok'] = files['ok'].replace(".txt", r"\main.ok.")
files['ng'] = files['ng'].replace(".txt", r"\main.ng.")
files['ps'] = files['ps'].replace(".txt", r".ps.")
files['ck'] = files['ck'].replace(".txt", r".ck.")

if files['ok'] == files['ng']:
    files['ok'] = os.path.join(filepath, ".ok.txt")
    files['ng'] = os.path.join(filepath, ".ng.txt")

print(f"Saving to  : {dfiles.get('ok', '')} / {files['ok']}")

# STATUS File
if ipv == "":
    ipv = "auto"

files['status'] = f"./STATUS/{ipv}-"
delold = f"/bin/rm {files['status']}*"
print(f"Deleting OLD Status File: {files['status']}")
os.system(delold)

current_time = time.localtime(time.time())
year = current_time.tm_year + 1900
month = current_time.tm_mon + 1
curdatestart = f"{year:04d}{month:02d}{current_time.tm_mday:02d}_{current_time.tm_hour:02d}{current_time.tm_min:02d}"
files['status'] = f"./STATUS/{ipv}-start-{curdatestart}"
os.system(f"touch {files['status']}")

# Inspect file to set operation mode
__opflag = ["Specified Domain Mode", "Mixed Domain Mode"]
_OPFLAG, _TDOMAIN = _inspect_file(filename)

_TDOMAIN = _TDOMAIN.strip()

print(f"Operation Mode : {_OPFLAG} {__opflag[_OPFLAG]} for {_TDOMAIN}")

# Retrieve MX if Operation FLAG is "Specified Domain"
if _OPFLAG == 0:
    _getMX(_TDOMAIN)
    WORKERS = _smtpserver[_TDOMAIN]['max']
    if 'thread' in _smtpserver[_TDOMAIN] and _smtpserver[_TDOMAIN]['thread']:
        THREADS = _smtpserver[_TDOMAIN]['thread']
    if _smtpserver[_TDOMAIN]['per'] > 0:
        per['thread'] = _smtpserver[_TDOMAIN]['per']
        per['pwait'] = _smtpserver[_TDOMAIN]['pwait'] * 10
        per['twait'] = _smtpserver[_TDOMAIN]['twait'] * 10
        per['swait'] = _smtpserver[_TDOMAIN]['swait']
    if THREADS > TOTALIP:
        THREADS = TOTALIP

if 'THREAD1' not in globals() or THREAD1 == "":
    THREADS = 1

print(f"Number of WORKERS {WORKERS}")
print(f"Number of Threads {THREADS}")
print(f"Number of transaction / threads {per['thread']}")
print(f"Delay times {per['pwait']} / {per['twait']} / {per['swait']}")
print(f"Total IP Numbers {TOTALIP}")

_divide_file(filename, WORKERS)

_prg['starttime'] = time.time()
if int(procid) > 0:
    _prg['starttime'] = time.time()
    updatestr = f"UPDATE zmfresult SET `zmf_from` = '{_prg['starttime']}' WHERE `id` = {procid};"
    mysqldb.db_open(DBNAME)
    mysqldb.db_execute(updatestr)
    mysqldb.db_close()

def manage_smtp_servers(WORKERS, _smtpserver, _TDOMAIN, filepath, filename, THREADS, _doline, _dolined, TOTALIP, _OPFLAG, _ipused, _ippause, iplist, per):
    global curserver, endcount
    
    for cloop in range(WORKERS):
        # Access SMTP Server Selection
        curserver += 1
        max_servers = _smtpserver[_TDOMAIN]['max']
        print(f"[{curserver}] MAX SMTP SERVER {max_servers}")

        if curserver > max_servers:
            curserver = 1

        # Fork Process
        try:
            pid = os.fork()
        except OSError as e:
            print(f"Fork failed: {e}")
            return
        
        if pid:
            pids.append(pid)
            continue
        else:
            openfile = f"{filepath}{filename}{cloop:02d}"
            print(f"[{cloop}] Child: {os.getpid()} for {cloop} : {openfile}")
            print(f"[{cloop}][{curserver}] {os.getpid()} Current SMTP Server : {_smtpserver[_TDOMAIN][curserver]}")

            if os.path.isfile(openfile):
                # Get number of data lines
                _linecnt = subprocess.getoutput(f"/usr/bin/wc -l {openfile}").split()
                _doline[cloop] = int(_linecnt[0])
                _dolined[cloop] = 0

                with open(openfile, 'r') as fin:
                    status = 0
                    while status == 0:
                        thr = []
                        print(f"[{cloop}] Status({status}) Beginning THREAD")

                        for thloop in range(THREADS):
                            if thloop < len(curpos) and curpos[thloop] != "":
                                print(f"[{cloop}][{thloop}] StoreVal_Begin({status}) : {curpos[thloop]}")

                        for thloop in range(THREADS):
                            emails = []
                            if thloop < len(curpos) and "@" in curpos[thloop]:
                                status = 0
                                emails = curpos[thloop].split(',')
                                print(f"[{cloop}] Split [{thloop}] {curpos[thloop]}")
                                curpos[thloop] = ""
                            else:
                                status, emails = _readdata()

                            ownip = get_valid_ip(TOTALIP, _OPFLAG, _ipused, _ippause, _TDOMAIN, iplist)

                            thread = threading.Thread(target=_thread_parent, args=(cloop, thloop, curserver, ownip, emails))
                            thread.start()
                            thr.append(thread)
                            print(f"[{cloop}][{thloop}] {os.getpid()} Status : {status}")

                            if status == 1 or _dolined[cloop] >= _doline[cloop]:
                                break

                        for thread in thr:
                            thread.join()

                        if per['twait'] > 0:
                            print(f"- Waiting for Thread WAIT {per['twait']}")
                            time.sleep(per['twait'] / 1_000_000)  # usleep equivalent
                            print("- Waiting for Thread WAIT; End")

                time.sleep(1)
                endcount += 1
                try:
                    os.unlink(openfile)
                except OSError as e:
                    print(f"Failed to delete file {openfile}: {e}")
            break

    wait_for_processes_to_end(pids)
    save_status_and_cleanup(filepath, endcount)

def get_valid_ip(TOTALIP, _OPFLAG, _ipused, _ippause, _TDOMAIN, iplist):
    ownip = random.randint(0, TOTALIP - 1)
    iploop = 0

    if _OPFLAG == 0:
        while _ipused[ownip] == 1 or _ippause.get(f"{_TDOMAIN}_{iplist[ownip]}", "") != "":
            ownip = random.randint(0, TOTALIP - 1)
            iploop += 1
            if iploop > 200:
                time.sleep(3)
                print(f"Checking IP Availabilities")
                _check_ippause()
                iploop = 0
        _ipused[ownip] = 1
    else:
        while _ippause.get(ownip, "") != "":
            ownip = random.randint(0, TOTALIP - 1)
            iploop += 1
            if iploop > 200:
                time.sleep(3)
                print(f"Checking IP Availabilities")
                _check_ippause()
                iploop = 0
    return ownip

def wait_for_processes_to_end(pids):
    while pids:
        child = pids.pop(0)
        pid, status = os.waitpid(child, os.WNOHANG)
        if pid == 0:  # No process ended yet
            pids.append(child)
        else:
            print(f"Finished: {child}")

def save_status_and_cleanup(filepath, endcount):
    _save_ippause()
    print(f"Saving IPStatus : {endcount}")

    if endcount == 1:
        print("Updating Status to End")
        ipv = "auto"
        status_file = f"./STATUS/{ipv}-"
        delold = f"/bin/rm {status_file}*"
        os.system(f"({delold}) >& /dev/null")

        sec, min, hour, mday, mon, year, *_ = time.localtime()
        year += 1900
        mon += 1
        curdatestart = f"{year:04d}{mon:02d}{mday:02d}_{hour:02d}{min:02d}"
        status_file = f"./STATUS/{ipv}-end-{curdatestart}"
        os.system(f"touch {status_file}")

        update_db_status()

def update_db_status():
    # Function to update the database status
    if procid > 0:
        if _workercount():
            print(f"[{ENDWORKDER}] Setting Done mark to {procid}")
            prg['endtime'] = int(time.time())
            updatestr = (
                f"UPDATE zmfresult SET zmf_executed = '-1', "
                f"zmf_putokfile = '{files['ok']}txt', "
                f"zmf_putngfile = '{files['ng']}txt', "
                f"zmf_end = '{prg['endtime']}' WHERE id = {procid};"
            )
            mysqldb.db_open(DBNAME)
            mysqldb.db_execute(updatestr)
            mysqldb.db_close()


# Global variables for IP pause handling
_ippause = {}
_ipused = {}

##
## Delete Original File if it is SUB Process
##
if pprocid > 0:
    tmpfile_path = os.path.join(filepath, tmpfilename)
    if os.path.isfile(tmpfile_path):
        try:
            os.remove(tmpfile_path)
            print(f"Deleted file: {tmpfile_path}")
        except OSError as e:
            print(f"Error deleting file {tmpfile_path}: {e}")

######
print(f"Start time: {start_time}")
endt_time = int(time.time())
print(f"End time: {endt_time}")

def _workercount(filepath, filename, WORKERS):
    """
    Increment the worker count stored in a file and check if it exceeds the number of allowed workers.
    If it exceeds, delete the count file and return 1 (indicating all workers are done).
    Otherwise, return 0.
    """
    countfile = os.path.join(filepath, f"{filename}cnt")
    curcnt = 0

    if os.path.isfile(countfile):
        try:
            with open(countfile, 'r') as f:
                curcnt = int(f.read().strip())
        except (OSError, ValueError) as e:
            print(f"Error reading count file {countfile}: {e}")
            curcnt = 0

    curcnt += 1

    # Define a path for the lock file
    lockfile = countfile + ".lock"
    
    # Create a FileLock object
    lock = FileLock(lockfile)

    # Use the lock to ensure exclusive access
    try:
        with lock:
            with open(countfile, 'w') as f:
                f.write(str(curcnt))
    except OSError as e:
        print(f"Error writing to count file {countfile}: {e}")
        return 0

    if curcnt > WORKERS:
        try:
            os.remove(countfile)
            print(f"Removed count file: {countfile}")
        except OSError as e:
            print(f"Error removing count file {countfile}: {e}")
        return 1
    
    return 0

## Read per thread data from file specified in per{thread}
def _readdata(file, per_thread, rcounters):
    """
    Reads a specified number of lines (per_thread) from a file.
    Updates the read counters and returns the read lines as emails along with the status.
    Status is 1 if the end of the file is reached, otherwise 0.
    """
    emails = []
    status = 0

    try:
        with open(file, 'r') as fin:
            for _ in range(per_thread):
                # Lock the counter
                with rcounters:
                    rcounters[0] += 1
                
                line = fin.readline()
                if not line:
                    status = 1
                    break
                
                # Remove any trailing newline characters
                line = line.rstrip('\r\n')
                emails.append(line)
    except OSError as e:
        print(f"Error reading file {file}: {e}")
        status = 1
    
    return status, emails

# Function to check IP pause
def _check_ippause_internal():
    """
    Process IP Pause
    "Need to Consider PAUSE Seconds"
    """
    curtime = time.time()
    pausetime = 30 if per.get('swait', 0) > 0 else 300

    to_remove = []
    for ippaused, timestamp in _ippause.items():
        passed = curtime - timestamp
        if passed > pausetime:
            to_remove.append(ippaused)

    for ippaused in to_remove:
        del _ippause[ippaused]
        print(f"Removed paused IP: {ippaused}")

def _save_ippause(overwrite=False):
    """
    Save the IP pause status to a file.
    If overwrite is True, the file will be overwritten; otherwise, it will be appended.
    """
    mode = 'w' if overwrite else 'a'
    try:
        with open(os.path.join(filepath, pausefile), mode) as pout:
            for ippaused, timestamp in _ippause.items():
                if timestamp:
                    pout.write(f'_ippause["{ippaused}"] = {timestamp};\n')
        print(f"IP pause status saved to file.")
    except OSError as e:
        print(f"Error saving IP pause status to file: {e}")

def _load_ippause():
    """
    Load the IP pause status from a file.
    """
    try:
        with open(os.path.join(filepath, pausefile), 'r') as pin:
            for line in pin:
                exec(line)
        _save_ippause(overwrite=True)
        print("IP pause status loaded and saved.")
    except OSError as e:
        print(f"Error loading IP pause status from file: {e}")

def _statusoutput(_tcounts, _dolined, _doline):
    """
    Output the current status of the processing.
    Displays the total processed lines and the total lines to be processed.
    """
    total = sum(_dolined.values())
    totals = sum(_doline.values())
    print(f"Current Status: {_tcounts} / {total} / {totals}")



# Example thread parent function
def _thread_parent(pnum, thnum, curserver, ownip, *emails):
    """
    Parent of thread execution
    """
    if procid > 0:
        try:
            mysqldb.db_open(_DBNAME)
        except Exception as e:
            print(f"Error opening database: {e}")
            return

    skipped = 0
    _ipused[ownip] = 1

    print(f"[{pnum}][{thnum}] $$ Opening SMTP Server : [{_OPFLAG}][{_TDOMAIN}][{curserver}] {_smtpserver[_TDOMAIN][curserver]} with IP [{ownip}] {iplist[ownip]}")

    yield_event = threading.Event()
    # Connect To Mail Server
    newmail = genMail()

    if _OPFLAG == 0:
        if openMail(_smtpserver[_TDOMAIN][curserver], iplist[ownip], newmail + _LOCAL['MAIL']):
            print(f"[{pnum}][{thnum}] Error : {_errorstr}")
            remails = ','.join(emails).replace(',,', ',').lstrip(',')
            
            # Sets IP PAUSE
            _ippause[f"{_TDOMAIN}_{iplist[ownip]}"] = time.time()
            _ipused[ownip] = 0
            print(f"---- [{pnum}][{thnum}] Error Returning : {_errorstr} for {len(emails)} {remails}")

            if procid > 0:
                try:
                    mysqldb.db_close()
                except Exception as e:
                    print(f"Error closing database: {e}")
            threading.current_thread().yield_event.wait(0)
            return remails


def _process_mail_address_cleaning(pnum, thnum, emails, ownip):
    """
    Process Mail Address Cleaning
    """
    yield_event = threading.Event()

    pdomain = ""
    trycount = 0

    for loop in range(len(emails)):
        if emails[loop] != "":
            if _OPFLAG == 1:
                _TDOMAIN = ""
                if "@" in emails[loop]:
                    _TDOMAIN = emails[loop].split('@')[1]
                
                if _TDOMAIN != pdomain:
                    _getMX(_TDOMAIN)
                    per['pwait'] = 0
                    per['twait'] = 0
                    per['swait'] = 0

                    if _smtpserver[_TDOMAIN]['pwait'] > 0:
                        per['pwait'] = _smtpserver[_TDOMAIN]['pwait']
                    if _smtpserver[_TDOMAIN]['twait'] > 0:
                        per['twait'] = _smtpserver[_TDOMAIN]['twait']
                    if _smtpserver[_TDOMAIN]['swait'] > 0:
                        per['swait'] = _smtpserver[_TDOMAIN]['swait']

                    curserver = _smtpserver[_TDOMAIN]['max']
                    if _smtpserver[_TDOMAIN]['max'] > 1:
                        curserver = random.randint(1, _smtpserver[_TDOMAIN]['max'])

                    if openMail(_smtpserver[_TDOMAIN][curserver], iplist[ownip], newmail + _LOCAL['MAIL']):
                        print(f"[{pnum}][{thnum}] (Mixed) Error : {_errorstr} ; {emails[loop]}")
                        trycount += 1
                        if trycount < 5:
                            print(f"[{pnum}][{thnum}] (Mixed) Sleeping")
                            time.sleep(10)
                            loop -= 1
                            continue
                        
                        # Skipping by Connect Error
                        try:
                            with open(_files['ck'] + "txt", 'a') as mfp:
                                mfp.write(emails[loop] + "\n")
                        except OSError as e:
                            print(f"Error writing to ck.txt: {e}")

                        if procid > 0:
                            try:
                                updatestr = f"UPDATE zmfresult SET zmf_putngcnt = zmf_putngcnt + 1 WHERE `id` = {procid};"
                                mysqldb.db_execute(updatestr)
                                if pprocid > 0:
                                    updatestr = f"UPDATE zmfresult SET zmf_putngcnt = zmf_putngcnt + 1 WHERE `id` = {pprocid};"
                                    mysqldb.db_execute(updatestr)
                            except Exception as e:
                                print(f"Error updating database: {e}")

                        emails[loop] = ""
                        continue

                    pdomain = _TDOMAIN

            trycount = 0
            verifyMail(emails[loop], pnum, 0)

            if not skipped:
                _dolined[pnum] += 1
                _tcounts += 1
                emails[loop] = ""
            else:
                # print(f"[{pnum}][{thnum}] Timeout Skipped {emails[loop]}")
                pass

            if per['pwait'] > 0:
                time.sleep(per['pwait'] / 1e6)  # Convert microseconds to seconds

    if SCK:
        try:
            SCK.sendall(f"RSET{_smtpcr}".encode())
            SCK.close()
        except Exception as e:
            print(f"Error closing socket: {e}")

    remails = ','.join(emails).replace(',,', ',').lstrip(',')

    threading.current_thread().yield_event.wait(0)
    _ipused[ownip] = 0

    if procid > 0:
        try:
            mysqldb.db_close()
            print(f"[{pnum}][{thnum}] DB Closed")
        except Exception as e:
            print(f"Error closing database: {e}")

    return remails

# Global dictionary to store MX server data
smtpserver = {}

def print_debug(message, tag=None):
    """
    Debugging utility to print messages if debugging is enabled.

    :param message: The message to print.
    :param tag: Optional tag to prepend to the message.
    """
    if DEBUG:
        cur = debug_cur
        if tag is not None and tag != "":
            cur = f"[{tag}]"
        print(f"{cur}{message}")

# Example usage
DEBUG = True  # Set to False to disable debugging
debug_cur = ""  # Set the initial debug prefix

# Call the function with a message and an optional tag
print_debug("This is a debug message.\n", "DEBUG_TAG")
