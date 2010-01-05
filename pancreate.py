import sys, os
import optparse

from fabric.api import local
from fabric.contrib.files import sed

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-n", "--project-name",
    action="store", dest="project_name",
    help="the name of the project to create")
parser.add_option("-d", "--domain",
    action="store", dest="domain",
    help="the name of the domain the site will be served on, by default")
parser.add_option("-a", "--appname",
    action="store", dest="appname",
    help="the name of the application to create")

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
        project_name = os.path.split(os.getcwd())[-1]
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
        local("echo domain: %(domain)s >> %(project_name)s/project.yaml" % locals())
        local("echo project_library: %(project_name)s >> %(project_name)s/project.yaml" % locals())
        local("echo hosts: [\"%(domain)s\"] >> %(project_name)s/project.yaml" % locals())

        open(os.path.join(project_name, "root.wsgi"), 'w').write(root_wsgi % locals())
 
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
