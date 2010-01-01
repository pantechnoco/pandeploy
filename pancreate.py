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

options, args = parser.parse_args()

root_wsgi = """
import os, sys

sys.path.append("/domains/pantechnoco.com/libs/")
os.environ['DJANGO_SETTINGS_MODULE'] = 'pantechnoco_site.settings'

from django.core.handlers import wsgi
application = wsgi.WSGIHandler()
"""

def main(argv):
    project_name = options.project_name or argv.pop(1)
    domain = options.domain or argv.pop(1)

    local("mkdir -p %(project_name)s/libs" % locals())
    local("mkdir -p %(project_name)s/static" % locals())
    local("cd %(project_name)s && django-admin.py startproject %(project_name)s" % locals())
    local("echo from pandeploy import \\* > %(project_name)s/fabfile.py" % locals())
    local("echo domain: %(domain)s >> %(project_name)s/project.yaml" % locals())
    local("echo project_library: %(project_name)s >> %(project_name)s/project.yaml" % locals())
    local("echo hosts: [\"%(domain)s\"] >> %(project_name)s/project.yaml" % locals())

    open(os.path.join(project_name, "root.wsgi"), 'w').write(root_wsgi)

    settings_path = os.path.join(project_name, project_name, "settings.py")
    settings = open(settings_path).read()
    settings = settings.replace(
        "DATABASE_ENGINE = ''",
        "DATABASE_ENGINE = 'sqlite3'")
    settings = settings.replace(
        "DATABASE_NAME = ''",
        "DATABASE_NAME = '/domains/%(domain)s/db.sqlite3'" % locals())
    open(settings_path, 'w').write(settings)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
