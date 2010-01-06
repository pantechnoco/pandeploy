from __future__ import with_statement
__all__ = ['clean', 'clean_all', 'deploy', 'domain', 'update_system', 'build', 'alias_version']

import os, sys

from fabric.state import env
from fabric.api import local, run, put
from fabric.context_managers import cd
from fabric.contrib.project import rsync_project

import djangorender

import yaml

def _dict_deep_update(target, source):
    for key, value in source.iteritems():
        if key in target:
            if isinstance(value, list):
                target[key] = target[key] + value
                continue
            elif isinstance(value, dict):
                _dict_deep_update(target[key], value)
                continue
        target[key] = value

project_config = yaml.load(open("project.yaml"))
if 'extends' in project_config:
    extends = yaml.load(open(project_config['extends']))
    _dict_deep_update(extends, project_config)
    project_config = extends

env.user = 'root'
env.hosts = project_config['hosts']
env.original_domain = project_config['domain']

target_dir = lambda p='': os.path.join('/domains/', env.domain, p)

# Exposed developer commands

def clean(glob):
    for f in (local, run):
        f("find . -name '%s' -exec rm {} \;" % (glob,))

def clean_all():
    clean('*.py[co]')
    clean('*~')

def domain(d, version=None):
    if version:
        env.domain = "%s.v.%s" % (version, d)
    else:
        env.domain = d
    project_config["domain"] = env.domain

    on_domain_change()

def on_domain_change():
    # Change other things that depend on domain
    env.domain_path = "/domains/%s/" % (env.domain,)
    env.main_library = project_config['project_library']

    build_project_version_yaml()

def build_project_version_yaml():
    original = open("project.yaml").read()
    this_version = original.replace(env.original_domain, env.domain)
    open("project_version.yaml", "w").write(this_version)

# Always run once with test domain first
domain(project_config["domain"], version=project_config["version"])

def build():
    build_settings()
    build_manage()
    build_wsgi()
    build_project_version_yaml()

def _build_from_template(src, dest):
    settings_template_path = os.path.join(os.path.dirname(__file__), src)
    settings_code = djangorender.render_path(settings_template_path, **project_config)
    open(dest, 'w').write(settings_code)

def build_settings():
    _build_from_template("settings.template", os.path.join(env.main_library, "settings.py"))

def build_manage():
    _build_from_template("manage.py.template", os.path.join(env.main_library, "manage.py"))

def build_wsgi():
    _build_from_template("wsgi.template", "root.wsgi") 

def deploy():
    clean_all()
    build()

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

    write_deploy_cfg()

def alias_version(version):
    original_domain = env.original_domain
    version_domain = "%s.v.%s" % (version, original_domain)
    project_config["alias_to"] = version_domain
    domain(original_domain)
    yaml.dump(project_config, open("project_version.yaml", "w"))

    write_deploy_cfg()

def write_deploy_cfg():
    put("project_version.yaml", target_dir("project.yaml"))

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
