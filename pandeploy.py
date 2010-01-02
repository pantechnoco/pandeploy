__all__ = ['clean', 'deploy', 'domain']

import os, sys

from fabric.state import env
from fabric.api import local, run, put
from fabric.contrib.project import rsync_project

import yaml

project_config = yaml.load(file("project.yaml"))

env.user = 'root'
env.hosts = project_config['hosts']

env.domain = project_config['domain']
env.domain_path = "/domains/%s/" % (env.domain,)
env.main_library = project_config['project_library']

target_dir = lambda p='': os.path.join('/domains/', env.domain, p)

def clean():
    local("find . -name '*.py[co]' -exec rm {} \;")

def domain(d):
    env.domain = d

def deploy():
    run("mkdir -p " + target_dir('libs'))
    run("mkdir -p " + target_dir('media'))
    run("mkdir -p " + target_dir('data'))

    rsync_project(local_dir="media", remote_dir="/domains/%s/" % env.domain)
    rsync_project(local_dir=env.main_library, remote_dir="/domains/%s/libs" % env.domain)
    rsync_project(local_dir="data", remote_dir="/domains/%s/" % env.domain)

    for local_dir in ('apps', 'libs'):
        for pkg_path in os.listdir(local_dir):
            rsync_project(
                local_dir=os.path.join(local_dir, pkg_path),
                remote_dir="/domains/%s/libs" % env.domain)

    run("find . -name '*.py[co]' -exec rm {} \;")
    run("cd %s && python libs/%s/manage.py syncdb --noinput" % (os.path.join('/domains/', env.domain), env.main_library))
    put("root.wsgi", target_dir("root.wsgi"))

