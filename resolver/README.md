# Resolver for ontology.neuinfo.org

Python scripts to generate nginx include files and nginx configuration
for the ontology.neuinfo.org and uri.neuinfo.org resolvers.

This resolver is built to make it possible to resolve fragment identifiers
where the fragment is not sent to the server by the browser.

NOTE! There is no way that we can resolve fragment ids without javascript,
anyone advanced enough to be resolving these using a script should use the
uri.neuinfo.org resolver or can convert `#` to `/` in the script themselves.

All ttl files are redirected to github master.
All owl files are redirected to github xml-final.

## nginx setup
1. Install the nginx lua module for your system (and optionally also compile nginx with luajit).
2. `git clone https://github.com/pintsized/lua-resty-http.git` to somewhere convenient.

## Setup
1. Run make_config.py to generate `ontology-uri-map.conf` `uri-ilx-map.conf` and `uri-scr-map.conf`.
2. Copy the map conf files and `nif-ont-resolver.conf` into `/etc/nginx/`.
3. Add `include nif-ont-resolver.conf` to the main http section of `/etc/nginx/nginx.conf`.
4. Place `redirect.html` and `redirect.js` in `/var/www/ontology` (adjust location as needed).
5. Copy `version-lookup.lua` and `json.lua` into `/etc/nginx/`.
6. Adjust the paths in all the config files to match the locations on your system.

# Auxillary services setup

In order to run aux services in ontree.py with caching to take the load off the webserver
there is a minimal nginx config that caches gzipped versions of files that are likely to
be slow to generate and only change rarely.

## nginx setup
1. `mkdir /var/cache/nginx` as root.
2. `cp aux-resolver.conf /etc/nginx/` as root.
3. Delete the default http section in the system default nginx file and replace it with
`include aux-resolver.conf;`.
