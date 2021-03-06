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
    for domain in os.listdir("/domains"):

        for domain_version in os.listdir(os.path.join("/", "domains", domain)):

            try:
                domain_version_cfg = yaml.load(open(os.path.join("/domains", domain, domain_version, "project.yaml")))
            except IOError:
                continue
            else:
                if 'alias_to' in domain_version_cfg:
                    aliases.setdefault(domain_version_cfg['alias_to'], []).append( domain_version if domain_version != 'public' else domain )
                else:
                    sites.append(domain_version_cfg)

    sites.sort(key=lambda site: site.get('apache_order', 0), reverse=True)
    for site in sites:
        domain_version = '.v.'.join((site['version'], site['domain']))
        if domain_version in aliases:
            site['domain_aliases'] = aliases[domain_version]

    httpd_conf = render_path("/etc/apache2/httpd.conf.template", sites=sites, test="foobarbaz")
    open("/etc/apache2/httpd.conf", 'w').write(httpd_conf)

    return 0

if __name__ == '__main__':
    sys.exit(main())
