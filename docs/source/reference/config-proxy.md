# Using a reverse proxy

In the following example, we show configuration files for a JupyterHub server
running locally on port `8000` but accessible from the outside on the standard
SSL port `443`. This could be useful if the JupyterHub server machine is also
hosting other domains or content on `443`. The goal in this example is to
satisfy the following:

* JupyterHub is running on a server, accessed *only* via `HUB.DOMAIN.TLD:443`
* On the same machine, `NO_HUB.DOMAIN.TLD` strictly serves different content,
  also on port `443`
* `nginx` or `apache` is used as the public access point (which means that
  only nginx/apache will bind  to `443`)
* After testing, the server in question should be able to score at least an A on the
  Qualys SSL Labs [SSL Server Test](https://www.ssllabs.com/ssltest/)

Let's start out with needed JupyterHub configuration in `jupyterhub_config.py`:

```python
# Force the proxy to only listen to connections to 127.0.0.1 (on port 8000)
c.JupyterHub.bind_url = 'http://127.0.0.1:8000'
```

(For Jupyterhub < 0.9 use `c.JupyterHub.ip = '127.0.0.1'`.)

For high-quality SSL configuration, we also generate Diffie-Helman parameters.
This can take a few minutes:

```bash
openssl dhparam -out /etc/ssl/certs/dhparam.pem 4096
```

## nginx

This **`nginx` config file** is fairly standard fare except for the two
`location` blocks within the main section for HUB.DOMAIN.tld.
To create a new site for jupyterhub in your nginx config, make a new file
in `sites.enabled`, e.g. `/etc/nginx/sites.enabled/jupyterhub.conf`:

```bash
# top-level http config for websocket headers
# If Upgrade is defined, Connection = upgrade
# If Upgrade is empty, Connection = close
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

# HTTP server to redirect all 80 traffic to SSL/HTTPS
server {
    listen 80;
    server_name HUB.DOMAIN.TLD;

    # Tell all requests to port 80 to be 302 redirected to HTTPS
    return 302 https://$host$request_uri;
}

# HTTPS server to handle JupyterHub
server {
    listen 443;
    ssl on;

    server_name HUB.DOMAIN.TLD;

    ssl_certificate /etc/letsencrypt/live/HUB.DOMAIN.TLD/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/HUB.DOMAIN.TLD/privkey.pem;

    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_prefer_server_ciphers on;
    ssl_dhparam /etc/ssl/certs/dhparam.pem;
    ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA';
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header Strict-Transport-Security max-age=15768000;

    # Managing literal requests to the JupyterHub front end
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # websocket headers
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;

        proxy_buffering off;
    }

    # Managing requests to verify letsencrypt host
    location ~ /.well-known {
        allow all;
    }
}
```

If `nginx` is not running on port 443, substitute `$http_host` for `$host` on
the lines setting the `Host` header.

`nginx` will now be the front facing element of JupyterHub on `443` which means
it is also free to bind other servers, like `NO_HUB.DOMAIN.TLD` to the same port
on the same machine and network interface. In fact, one can simply use the same
server blocks as above for `NO_HUB` and simply add line for the root directory
of the site as well as the applicable location call:

```bash
server {
    listen 80;
    server_name NO_HUB.DOMAIN.TLD;

    # Tell all requests to port 80 to be 302 redirected to HTTPS
    return 302 https://$host$request_uri;
}

server {
    listen 443;
    ssl on;

    # INSERT OTHER SSL PARAMETERS HERE AS ABOVE
    # SSL cert may differ

    # Set the appropriate root directory
    root /var/www/html

    # Set URI handling
    location / {
        try_files $uri $uri/ =404;
    }

    # Managing requests to verify letsencrypt host
    location ~ /.well-known {
        allow all;
    }

}
```

Now restart `nginx`, restart the JupyterHub, and enjoy accessing
`https://HUB.DOMAIN.TLD` while serving other content securely on
`https://NO_HUB.DOMAIN.TLD`.

### SELinux permissions for nginx
On distributions with SELinux enabled (e.g. Fedora), one may encounter permission errors
when the nginx service is started.

We need to allow nginx to perform network relay and connect to the jupyterhub port. The
following commands do that:

```bash
semanage port -a -t http_port_t -p tcp 8000
setsebool -P httpd_can_network_relay 1
setsebool -P httpd_can_network_connect 1
```
Replace 8000 with the port the jupyterhub server is running from.


## Apache

As with nginx above, you can use [Apache](https://httpd.apache.org) as the reverse proxy.
First, we will need to enable the apache modules that we are going to need:

```bash
a2enmod ssl rewrite proxy proxy_http proxy_wstunnel
```

Our Apache configuration is equivalent to the nginx configuration above:

- Redirect HTTP to HTTPS
- Good SSL Configuration
- Support for websockets on any proxied URL
- JupyterHub is running locally at http://127.0.0.1:8000

```bash
# redirect HTTP to HTTPS
Listen 80
<VirtualHost HUB.DOMAIN.TLD:80>
  ServerName HUB.DOMAIN.TLD
  Redirect / https://HUB.DOMAIN.TLD/
</VirtualHost>

Listen 443
<VirtualHost HUB.DOMAIN.TLD:443>

  ServerName HUB.DOMAIN.TLD

  # configure SSL
  SSLEngine on
  SSLCertificateFile /etc/letsencrypt/live/HUB.DOMAIN.TLD/fullchain.pem
  SSLCertificateKeyFile /etc/letsencrypt/live/HUB.DOMAIN.TLD/privkey.pem
  SSLProtocol All -SSLv2 -SSLv3
  SSLOpenSSLConfCmd DHParameters /etc/ssl/certs/dhparam.pem
  SSLCipherSuite EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH

  # Use RewriteEngine to handle websocket connection upgrades
  RewriteEngine On
  RewriteCond %{HTTP:Connection} Upgrade [NC]
  RewriteCond %{HTTP:Upgrade} websocket [NC]
  RewriteRule /(.*) ws://127.0.0.1:8000/$1 [P,L]

  <Location "/">
    # preserve Host header to avoid cross-origin problems
    ProxyPreserveHost on
    # proxy to JupyterHub
    ProxyPass         http://127.0.0.1:8000/
    ProxyPassReverse  http://127.0.0.1:8000/
  </Location>
</VirtualHost>
```

 
In case of the need to run the jupyterhub under /jhub/ or other location please use the below configurations:
- JupyterHub running locally at http://127.0.0.1:8000/jhub/ or other location

httpd.conf amendments:
```bash
 RewriteRule /jhub/(.*) ws://127.0.0.1:8000/jhub/$1 [NE.P,L]
 RewriteRule /jhub/(.*) http://127.0.0.1:8000/jhub/$1 [NE,P,L]
 
 ProxyPass /jhub/ http://127.0.0.1:8000/jhub/
 ProxyPassReverse /jhub/  http://127.0.0.1:8000/jhub/
 ```
 
jupyterhub_config.py amendments:
 ```bash
  --The public facing URL of the whole JupyterHub application.
  --This is the address on which the proxy will bind. Sets protocol, ip, base_url
  c.JupyterHub.bind_url = 'http://127.0.0.1:8000/jhub/'
  ```
