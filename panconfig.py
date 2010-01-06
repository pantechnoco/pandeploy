#!/usr/bin/env python

"""
panconfig.py - server-side configuration generator.

panconfig.py is pushed to the server and run by the deployment scripts to generate updated
configurations from the pushed domain content. Currently, this means getting static and wsgi
settings from each domain's project.yaml and generating Apache's httpd.conf to serve each
domain properly.
"""

import sys, os

from djangorender import render_path
import yaml

def main():
    sites = []
    aliases = {}
    for site in os.listdir("/domains"):
        try:
            site_cfg = yaml.load(open(os.path.join("/domains", site, "project.yaml")))
        except IOError:
            continue
        else:
            print site_cfg['domain'], site_cfg.get('alias_to'), site
            if 'alias_to' in site_cfg:
                aliases.setdefault(site_cfg['alias_to'], []).append( site_cfg['domain'] )
            else:
                sites.append(site_cfg)

    sites.sort(key=lambda site: site.get('default', 'no') == 'no')
    print "aliases", aliases
    for site in sites:
        if site['domain'] in aliases:
            site['domain_aliases'] = aliases[site['domain']]

    httpd_conf = render_path("/etc/apache2/httpd.conf.template", sites=sites, test="foobarbaz")
    open("/etc/apache2/httpd.conf", 'w').write(httpd_conf)

    return 0

if __name__ == '__main__':
    sys.exit(main())
