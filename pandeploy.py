__all__ = ['clean', 'deploy', 'domain']

import os

from fabric.state import env
from fabric.api import local, run, put

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

def put_directory(local_path, remote_path):
    local("tar -cjf /tmp/transpackage.tbz %s" % (local_path,))
    put("/tmp/transpackage.tbz", "/tmp/transpackage.tbz")
    run("cd %s && tar -xjf /tmp/transpackage.tbz" % (remote_path,))

def domain(d):
    env.domain = d

def deploy():
    run("mkdir -p " + target_dir('libs'))
    run("mkdir -p " + target_dir('static'))

    put_directory("static", os.path.join('/domains/', env.domain))
    put_directory(env.main_library, target_dir("libs"))

    run("cd %s && python libs/%s/manage.py syncdb --noinput" % (os.path.join('/domains/', env.domain), env.main_library))
    put("root.wsgi", target_dir("root.wsgi"))

