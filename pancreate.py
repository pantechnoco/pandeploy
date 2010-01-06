import sys, os

from fabric.api import local
from fabric.contrib.files import sed

import yaml

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-n", "--project-name",
    action="store", dest="project_name",
    help="(required) the name of the project to create")
parser.add_option("-d", "--domain",
    action="store", dest="domain",
    help="the name of the domain the site will be served on, by default")
parser.add_option("-a", "--appname",
    action="store", dest="appname",
    help="the name of the application to create")
parser.add_option("-e", "--extends",
    action="store", dest="extends",
    help="the name of a project whose project.yaml will be extended")

options, args = parser.parse_args()

root_wsgi = """
import os, sys

sys.path.append("/domains/%(domain)s/libs/")
os.environ['DJANGO_SETTINGS_MODULE'] = '%(project_name)s.settings'

from django.core.handlers import wsgi
application = wsgi.WSGIHandler()
"""

def main(argv):
    project_name = options.project_name
    if not project_name:
        sys.argv = ['pancreate.py', '--help']
        parser.parse_args()
        return 1
    domain = options.domain
    appname = options.appname

    def mkdir(dir, L):
        local(("mkdir -p %(project_name)s/" % L) + dir)

    if appname:
        local("cd apps && django-admin.py startapp %s" % (appname,))

    else:

        mkdir("libs", locals())
        mkdir("media", locals())
        mkdir("apps", locals())

        local("cd %(project_name)s && django-admin.py startproject %(project_name)s" % locals())
        local("echo from pandeploy import \\* > %(project_name)s/fabfile.py" % locals())
        local("echo project_library: %(project_name)s >> %(project_name)s/project.yaml" % locals())
        local("echo hosts: [\"%(domain)s\"] >> %(project_name)s/project.yaml" % locals())

        cfg_file = open(os.path.join(project_name, "project.yaml"), 'w')
        cfg = {
            'domain': domain,
            'version': "0.1",
            'project_library': project_name,
            'DEBUG': True,
        }
        if options.extends:
            cfg['extends'] = os.path.join("..", options.extends, "project.yaml")
        yaml.dump(cfg, cfg_file)
        cfg_file.close()

        open(os.path.join(project_name, "root.wsgi"), 'w').write(root_wsgi % locals())
 
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
