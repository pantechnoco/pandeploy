import sys, os
import optparse

from fabric.api import local

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-n", "--project-name",
    action="store", dest="project_name",
    help="the name of the project to create")
parser.add_option("-d", "--domain",
    action="store", dest="domain",
    help="the name of the domain the site will be served on, by default")

options, args = parser.parse_args()

def main(argv):
    project_name = options.project_name or argv.pop(1)
    domain = options.domain or argv.pop(1)

    local("mkdir -p %(project_name)s/libs" % locals())
    local("mkdir -p %(project_name)s/static" % locals())
    local("cd %(project_name)s && django-admin.py startproject %(project_name)s" % locals())
    local("echo from pandeploy import \\* > %(project_name)s/fabfile.py" % locals())
    local("echo domain: %(domain)s >> %(project_name)s/project.yaml" % locals())
    local("echo project_library: %(project_name)s >> %(project_name)s/project.yaml" % locals())
    local("echo hosts: %(domain)s >> %(project_name)s/project.yaml" % locals())

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
