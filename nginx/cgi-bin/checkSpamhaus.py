import sys
import os
import dns.resolver

def check_spamhaus(iplist, name_server=None):
    # Initialize the resolver with the specified name server or default one
    resolver = dns.resolver.Resolver()
    if name_server:
        resolver.nameservers = [name_server]

    # Assuming persistent_udp is similar to setting `use_edns` in dnspython
    resolver.use_edns(0, 0, 512)

    cnt_ok = 0
    cnt_ng = 0
    iplist_ng = []

    for ipaddr in iplist:
        if not ipaddr:
            continue

        # Reverse the IP address
        reversed_ip = '.'.join(reversed(ipaddr.split('.')))
        query = f"{reversed_ip}.zen.spamhaus.org"

        try:
            record = resolver.resolve(query, 'A')
            # If record is found, the IP is listed in Spamhaus
            cnt_ng += 1
            iplist_ng.append(ipaddr)
            print(f'iplist_ng[{cnt_ng}] = "{ipaddr}";    # NG')

            # For debug:
            # print("NG")
            # for rr in record:
            #     print(rr.to_text())

        except dns.resolver.NXDOMAIN:
            # If no record is found, the IP is not listed
            cnt_ok += 1
            print(f'iplist[{cnt_ok}] = "{ipaddr}";    # OK')

            # For debug:
            # print("OK")
            # print(f'ErrorString : {resolver.error}')

    return iplist_ng

def main(ipfile):
    if not ipfile:
        print("-ipfile=<iplist filename> must be specified")
        sys.exit(1)

    if not os.path.isfile(ipfile):
        print(f"{ipfile} file does not exist")
        sys.exit(1)

    with open(ipfile, 'r') as f:
        iplist = [line.strip() for line in f if line.strip()]

    # Use the global NAME_SERVER variable if defined
    name_server = '208.67.222.222'  # OpenDNS Home
    check_spamhaus(iplist, name_server)

if __name__ == '__main__':
    ipfile = None
    for arg in sys.argv:
        if arg.startswith('-ipfile='):
            ipfile = arg.split('=', 1)[1]
            break

    main(ipfile)
