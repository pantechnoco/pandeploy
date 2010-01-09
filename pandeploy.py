from __future__ import with_statement
__all__ = ['clean', 'clean_all', 'deploy', 'domain', 'update_system', 'build', 'alias', 'alias_version', 'purge_old', 'purge', 'test']

import os, sys

from fabric.state import env
from fabric.api import local, run, put, get
from fabric.context_managers import cd
from fabric.contrib.project import rsync_project

import djangorender

import yaml

# Utility functions

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

def _init_d(service, command):
    run("/etc/init.d/%s %s" % (service, command))

# Configuration loading

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
    clean("root.wsgi")
    clean("project_version.yaml")
    local("rm -f %s/settings.py" % (env.main_library,))
    local("rm -f %s/manage.py" % (env.main_library,))

def domain(d, version=None):
    if version:
        env.domain = "%s.v.%s" % (version, d)
    else:
        env.domain = d
    project_config["domain"] = env.domain

     # Change other things that depend on domain
    env.domain_path = "/domains/%s/" % (env.domain,)
    env.main_library = project_config['project_library']

    build_project_version_yaml()

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

def build_project_version_yaml():
    reverted = dict(project_config)
    reverted['domain'] = env.original_domain
    yaml.dump(reverted, open("project_version.yaml", "w"))
    original = open("project_version.yaml").read()
    this_version = original.replace(env.original_domain, env.domain)
    open("project_version.yaml", "w").write(this_version)

def deploy():
    if project_config["version"] == active_version():
        print "-------------------------------------"
        print "Refusing to deploy to active version."
        return -1

    clean_all()
    build()

    run("if [ -d /domains/%(domain)s/ ]; then echo; else if [ -d /domains/%(original_domain)s/ ]; \
        then cp -R /domains/%(original_domain)s /domains/%(domain)s; fi; fi" %
        {'domain': env.domain, 'original_domain': env.original_domain})
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

def purge(domain):
    run('rm -fr /domains/%s' % (domain,))

def purge_old():
    run('find /domains -name "*.v.%s" -not -name "%s*" -exec rm -fr {} \;' % (env.original_domain, active_version()))

def alias_version(version):
    if version == "current":
        version = project_config["version"]
    version_domain = "%s.v.%s" % (version, env.original_domain)
    alias(env.original_domain, version_domain)

def alias(from_domain, to_domain):
    run("mkdir -p /domains/%s" % (from_domain,))
    project_config["alias_to"] = to_domain
    domain(from_domain)
    yaml.dump(project_config, open("project_version.yaml", "w"))

    write_deploy_cfg()

def write_deploy_cfg():
    put("project_version.yaml", target_dir("project.yaml"))

    update_system()

def test(verbose=False):
    run(("cd /domains/%(domain)s && python libs/%(project_library)s/manage.py test -v " + ('2' if verbose else '1')) % project_config)

# Server side commands

def active_version():
    try:
        get(os.path.join("/", "domains", env.original_domain, "project.yaml"), "/tmp/current.yaml")
    except:
        return
    else:
        current = yaml.load(open("/tmp/current.yaml"))
        return current["version"]

def update_system():
    put(os.path.join(os.path.dirname(__file__), "panconfig.py"), os.path.join("/", "usr", "bin", "panconfig.py"))
    put(os.path.join(os.path.dirname(__file__), "djangorender.py"), os.path.join("/", "usr", "lib", "python2.6", "dist-packages", "djangorender.py"))
    put(os.path.join(os.path.dirname(__file__), "httpd.conf.template"), os.path.join("/", "etc", "apache2"))

    run("panconfig.py")

    _init_d('apache', 'reload')

# Always run once with test domain first
domain(project_config["domain"], version=project_config["version"])

