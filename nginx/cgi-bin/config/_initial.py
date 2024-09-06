import socket
import urllib.parse

cgi = {
    'name': "zfm.cgi",
    'url': "zfm.cgi",
    'uploadurl': "zfm.cgi"
}

cgi['servername'] = socket.gethostname().split('.')[0]
cgi['mode'] = "indiv"

LOCAL = False  # Set this according to your local environment

if LOCAL:
    cgi['exepath'] = "http://localhost/zfm/"
else:
    cgi['exepath'] = "/zmf/"

def url_encode(s):
    return urllib.parse.quote_plus(s)

def url_decode(s):
    return urllib.parse.unquote_plus(s)
