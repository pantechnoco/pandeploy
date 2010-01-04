from __future__ import with_statement
__all__ = ['clean', 'clean_all', 'deploy', 'domain', 'update_system', 'build_settings']

import os, sys

from fabric.state import env
from fabric.api import local, run, put
from fabric.context_managers import cd
from fabric.contrib.project import rsync_project

import djangorender

import yaml

project_config = yaml.load(file("project.yaml"))

env.user = 'root'
env.hosts = project_config['hosts']

env.domain = project_config['domain']
env.domain_path = "/domains/%s/" % (env.domain,)
env.main_library = project_config['project_library']

target_dir = lambda p='': os.path.join('/domains/', env.domain, p)

# Exposed developer commands

def clean(glob):
    for f in (local, run):
        f("find . -name '%s' -exec rm {} \;" % (glob,))

def clean_all():
    clean('*.py[co]')
    clean('*~')

def domain(d):
    env.domain = d

def build():
    build_settings()

def build_settings():
    settings_template_path = os.path.join(os.path.dirname(__file__), "settings.template")
    settings_code = djangorender.render_path(settings_template_path, **project_config)
    open(os.path.join(env.main_library, "settings.py"), 'w').write(settings_code)

def deploy():
    clean_all()

    run("mkdir -p " + target_dir('libs'))

    for directory in ('media', 'data', 'templates'):
        if os.path.exists(directory):

            run("mkdir -p " + target_dir(directory))
            rsync_project(local_dir=directory, remote_dir="/domains/%s/" % env.domain)

    rsync_project(local_dir=env.main_library, remote_dir="/domains/%s/libs" % env.domain)

    for local_dir in ('apps', 'libs'):
        if os.path.exists(local_dir):
            for pkg_path in os.listdir(local_dir):
                rsync_project(
                    local_dir=os.path.join(local_dir, pkg_path),
                    remote_dir="/domains/%s/libs" % env.domain)

    run("find . -name '*.py[co]' -exec rm {} \;")
    with cd(os.path.join('/domains/', env.domain)):
        run("python libs/%s/manage.py syncdb --noinput" % (env.main_library,))
    put("root.wsgi", target_dir("root.wsgi"))
    put("project.yaml", target_dir("project.yaml"))

    update_system()

# Server side commands

def update_system():
    put(os.path.join(os.path.dirname(__file__), "panconfig.py"), os.path.join("/", "usr", "bin", "panconfig.py"))
    put(os.path.join(os.path.dirname(__file__), "djangorender.py"), os.path.join("/", "usr", "lib", "python2.6", "dist-packages", "djangorender.py"))
    put(os.path.join(os.path.dirname(__file__), "httpd.conf.template"), os.path.join("/", "etc", "apache2"))

    run("panconfig.py")

    reload_apache()

def reload_apache():
    run("/etc/init.d/apache2 reload")
