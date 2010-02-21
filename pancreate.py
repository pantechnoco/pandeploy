#!/usr/bin/env python
from __future__ import with_statement

import sys, os

from fabric.api import local
from fabric.contrib.files import sed
from fabric.context_managers import cd

import yaml

from pandeploy.component import ComponentLoader
from pandeploy.project import Project
from pandeploy import no_warning

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

    project = Project()
    project.name = project_name
    project.domain = domain
    project.appname = appname
    project.path = os.path.abspath(os.path.join('.', project_name))

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
            os.symlink(os.path.join('..', options.extends, 'project.yaml'), os.path.join(project_name, 'project_extends.yaml'))
        yaml.dump(cfg, cfg_file)
        cfg_file.close()

        open(os.path.join(project_name, "root.wsgi"), 'w').write(root_wsgi % locals())

        gitignore_template = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pandeploy', 'skel', 'default_gitignore'))
        with cd(project_name):
            with no_warning:
                local('python -m djangorender -p %(gitignore_template)s -s project_name=%(project_name)s > .gitignore' % locals())
            local('git init')
            local('git add .')
            local("git commit -m 'initial commit'")

        CL = ComponentLoader()
        CL.load_all()
        for name, component in CL.components.items():
            component.populate_new_project(project)

        username = os.environ.get('USER')
        with cd(project_name):
            local("fab allow_deploy:%(username)s" % locals())
            local("fab allow_alias:%(username)s" % locals())
            local("fab deploy alias_version:0.1" % locals())
 
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
