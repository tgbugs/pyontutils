# Resolver for ontology.neuinfo.org

Python scripts to generate nginx include files and
nginx configuration for ontology.neuinfo.org resolver.

This resolver is built to make it possible to resolve fragment identifiers
where the fragment is not sent to the server by the browser.

NOTE! There is no way that we can resolve these without javascript, anyone
who is advanced enough to be trying to resolve these using a script should
be using the uri.neuinfo.org resolver or can convert `#` to `/` on the fly.

All ttl files are redirected to github master.
All owl files are redirected to github xml-final.

# Setup
1. Run make_config.py to generate `ontology-uri-map.conf`
2. Copy `ontology-uri-map.conf` and `nif-ont-resolver.conf` into /etc/nginx/
3. Add `include nif-ont-resolver.conf` to the main http section of /etc/nginx/nginx.conf
4. Place `redirect.html` and `redirect.js` in `/var/www/ontology` (adjust location as needed)
