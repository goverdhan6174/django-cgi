# Use the official Nginx base image
FROM nginx:latest

# Install necessary packages including fcgiwrap and spawn-fcgi
RUN apt-get update && apt-get install -y fcgiwrap spawn-fcgi python3 perl libfcgi-perl libnet-dns-perl

# Copy the Nginx configuration file
COPY nginx.conf /etc/nginx/nginx.conf

# Create CGI-BIN directories and copy CGI scripts
RUN mkdir -p /usr/lib/cgi-bin

# Copy CGI scripts into the container (assumes you have a local cgi-bin folder with scripts)
COPY cgi-bin/ /usr/lib/cgi-bin/

# Set permissions for CGI scripts to be executable
RUN chmod +x /usr/lib/cgi-bin/*.cgi
RUN chmod +x /usr/lib/cgi-bin/*.py
RUN chmod +x /usr/lib/cgi-bin/*.pl

# Ensure the /var/run directory exists and is writable
RUN mkdir -p /var/run && chmod 777 /var/run

# Expose port 80
EXPOSE 80

# Start fcgiwrap and Nginx
CMD spawn-fcgi -s /var/run/fcgiwrap.socket -M 766 /usr/sbin/fcgiwrap && nginx -g "daemon off;"
