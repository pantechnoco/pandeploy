from __future__ import with_statement
__all__ = [
    'clean',
    'clean_all',
    'deploy',
    'install_requirements',
    'domain',
    'update_system',
    'build',
    'alias',
    'alias_version',
    'purge_old',
    'purge',
    'test',
    'setup_domain',
    'allow_deploy', 'deny_deploy',
    'allow_alias', 'deny_alias',
]

import os, sys
import copy
import hashlib

from fabric.state import env
from fabric.api import local, run, sudo, put, get
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

def _dict_deep_combine(A, B):
    A = copy.deepcopy(A)
    _dict_deep_update(A, B)
    return A

def _init_d(service, command):
    run("/etc/init.d/%s %s" % (service, command))

def target_dir(path='', version=None, domain=None):
    """Produce a path within a domain on the host.

    path: a relative path within the domain's directory
    version: the specific version of a domain to find the directory for,
        or None if the current version should be used,
        or "public" if the public domain directory should be used.
    domain: the name of the domain without version
    """

    if version == 'public':
        domain = env.domain
        return os.path.join('/domains/', domain, 'public', path)

    else:
        if version is None:
            version = project_config["version"]
        version_domain = Domain(domain or env.domain, version).version_domain

        return os.path.join('/domains/', domain or env.domain, version_domain, path)

def sync_dirs(local_dir, remote_dir, **kwargs):

    rsync_project(local_dir=local_dir, remote_dir=remote_dir, extra_opts="--no-p -Ok", **kwargs)

class Domain(object):

    shorthash_length = 20

    def __init__(self, domain=None, version=None):
        self.domain = domain
        self.version = version

    @property
    def version_domain(self, version=None):
        if version:
            return Domain(self.domain, version).version_domain
        if self.version:
            return '.v.'.join((self.version, self.domain))
        else:
            return self.domain

    @classmethod
    def parse(cls, domain_string):
        if '.v.' in domain_string:
            return cls(*domain_string.split('.v.'))
        else:
            return cls(domain_string)

    @property
    def shorthash(self):
        return hashlib.sha1(self.domain).hexdigest()[:self.shorthash_length]

    @property
    def domain_group(self):
        return "DD%s" % (self.shorthash,)

    @property
    def domain_alias_group(self):
        return "DA%s" % (self.shorthash,)

class _NoWarning(object):
    """Used to suppress warning messages when commands are OK to have non-0 exit.

    Usage:

        with no_warning:
            run("adduser username")
    """

    def __enter__(self, *args):
        from fabric import operations

        self.orig_warn = operations.warn
        self.orig_warn_flag = env.warn_only

        operations.warn = lambda x: True
        env.warn_only = True

    def __exit__(self, *args):
        from fabric import operations

        env.warn_only = self.orig_warn_flag
        operations.warn = self.orig_warn

no_warning = _NoWarning()

# Configuration loading

def load_and_merge(base_path, extended_path):
    """Loads YAML from base_path and extended_path and updates the base with
    the extended configuration. The result is a dict.
    """

    ext_config = yaml.load(open(extended_path))
    base_config = yaml.load(open(base_path))
    return _dict_deep_combine(base_config, ext_config)

project_config = load_and_merge("project_extends.yaml", "project.yaml")

env.user = project_config['user']
env.hosts = project_config['hosts']
env.domain = project_config['domain']

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

    domain = Domain.parse(d)
    if version is None:
        version = project_config["version"]
    domain.version = version
    env.domain = domain.domain

    env.version_domain = domain.version_domain 

    project_config["domain"] = env.domain
    project_config["version_domain"] = env.version_domain

     # Change other things that depend on domain
    env.main_library = project_config['project_library']

    build_project_version_yaml()

def build():
    build_settings()
    build_manage()
    build_wsgi()
    build_project_version_yaml()

def _build_from_template(src, dest, **extra_settings):
    conf = copy.deepcopy(project_config)
    conf.update(extra_settings)

    settings_template_path = os.path.join(os.path.dirname(__file__), src)
    settings_code = djangorender.render_path(settings_template_path, **conf)
    open(dest, 'w').write(settings_code)

def build_settings():
    # Build local settings
    _build_from_template("settings.template", os.path.join(env.main_library, "settings.py"), project_path='.')
    # Build remote settings
    _build_from_template("settings.template", os.path.join(env.main_library, "remote_settings.py"),
        project_path=os.path.join('/', 'domains', env.domain, '%s.v.%s' % (project_config['version'], env.domain)))

def build_manage():
    _build_from_template("manage.py.template", os.path.join(env.main_library, "manage.py"))

def build_wsgi():
    _build_from_template("wsgi.template", "root.wsgi") 

def build_project_version_yaml():
    yaml.dump(project_config, open("project_version.yaml", "w"))

# Server Setup

def _setup_domain_rights(domain):
    """Configure a user and group to own the domain."""

    # Names have to stay at 32 characters or less, so
    # we take each domain and map it to a hash.
    domain_group = Domain(domain).domain_group
    domain_alias_group = Domain(domain).domain_alias_group

    with no_warning:
        sudo("adduser --group --system --disabled-password %s" % (domain_group,))
        sudo("adduser --group --system --disabled-password %s" % (domain_alias_group,))

    # Updating previous domain users
    sudo("usermod --shell /bin/bash %s" % (Domain(domain).domain_group,))
    sudo("usermod --shell /bin/bash %s" % (Domain(domain).domain_alias_group,))

    sudo("mkdir -p /home/%s/.ssh/" % (domain,))
    sudo("touch /home/%s/.ssh/authorized_keys" % (domain,))
    sudo("chown -R %s:%s /domains/%s" % (domain_group, domain_group, domain))
    sudo("chmod -R g+w /domains/%s" % (domain,))
    sudo("chmod -R g-w /domains/%s/public" % (domain,))

def _setup_domain_dir(domain):
    sudo("mkdir -p /domains/%s/public" % (domain,))

def _setup_domain_keys(domain):
    # This finds all users in the domain's group and populates the domain with their keys
    sudo("rm -f /home/%s/.ssh/authorized_keys" % (domain,))
    sudo("getent group|grep '^%s'|cut -d: -f4|tr -d '\n'|xargs -L 1 -d , -I {} bash -c 'if [ \"{}\" != \" \" ]; then if [ \"{}\" != \"%s\" ]; then cat /home/{}/.ssh/authorized_keys; fi; fi' >> /home/%s/.ssh/authorized_keys" % (Domain(domain).domain_alias_group, domain, domain))

def setup_domain(domain=None):
    """Configures various expected things for a domain before deployment."""

    domain = domain or env.domain

    _setup_domain_dir(domain)
    _setup_domain_rights(domain)
    _setup_domain_keys(domain)

def allow_deploy(user, domain=None):
    domain = domain or env.domain
    setup_domain(domain)

    sudo("adduser %s %s" % (user, Domain(domain).domain_group))

def deny_deploy(user, domain=None):
    domain = domain or env.domain
    setup_domain(domain)

    sudo("deluser %s %s" % (user, Domain(domain).domain_group))

def allow_alias(user, domain=None):
    domain = domain or env.domain

    sudo("adduser %s %s" % (user, Domain(domain).domain_alias_group))
    setup_domain(domain)

def deny_alias(user, domain=None):
    domain = domain or env.domain

    sudo("deluser %s %s" % (user, Domain(domain).domain_alias_group))
    setup_domain(domain)

# Deployment

def deploy():

    setup_domain()

    if project_config["version"] == active_version():
        print "-------------------------------------"
        print "Refusing to deploy to active version."
        return -1

    clean_all()
    build()

    current_domain = Domain(env.domain, active_version()).version_domain

    # If this version has never been deployed to this machine before,
    # and a previous version exists on it,
    # copy the previous version as the base of the new.

    run("if [ -d %(new_version_path)s ]; then echo; else if [ -d %(current_version_path)s ]; \
        then cp -R %(current_version_path)s %(new_version_path)s; fi; fi" %

        {'current_version_path': target_dir(version=active_version()),
         'new_version_path': target_dir(version=project_config['version'])})

    run("mkdir -p " + target_dir('libs'))

    for directory in ('media', 'data', 'templates'):
        if os.path.exists(directory):

            run("mkdir -p " + target_dir(directory))
            sync_dirs(local_dir=directory, remote_dir=target_dir())

    sync_dirs(local_dir=env.main_library, remote_dir=target_dir('libs'), exclude="settings.py")
    sync_dirs(local_dir=os.path.join(env.main_library, "remote_settings.py"), remote_dir=target_dir(os.path.join('libs', env.main_library, 'settings.py')))

    for local_dir in ('apps', 'libs'):
        if os.path.exists(local_dir):
            for pkg_path in os.listdir(local_dir):
                local_path = os.path.join(local_dir, pkg_path)
                if os.path.isdir(local_path):
                    sync_dirs(
                        local_dir=local_path,
                        remote_dir=target_dir('libs'))
                else:
                    put(local_path, target_dir(os.path.join('libs', pkg_path)))

    run("find . -name '*.py[co]' -exec rm {} \;")
    with cd(os.path.join(target_dir())):
        run("python libs/%s/manage.py syncdb --noinput" % (env.main_library,))
    sync_dirs(local_dir="root.wsgi", remote_dir=target_dir("root.wsgi"))

    install_requirements()

    write_deploy_cfg()

def install_requirements():
    # Install requirements.txt
    if os.path.exists("requirements.txt"):
        sync_dirs(local_dir="requirements.txt", remote_dir=target_dir("requirements.txt"))
        sudo('virtualenv --no-site-packages %s' % (target_dir('ve')))
        run('pip install -E %s -r %s' % (target_dir('ve'), target_dir('requirements.txt'),))

def purge(domain, version):
    run('rm -fr ' + target_dir(domain=domain, version=version))

def purge_old():
    sudo('find /domains/%s -name "*.v.%s" -not -name "%s*" -prune -exec rm -fr {} \;' % (env.domain, env.domain, active_version()))

def alias_version(version):
    if version == "current":
        version = project_config["version"]
    version_domain = Domain(env.domain, version).version_domain
    alias(env.domain, version_domain)

def as_user(user):
    def D(f):
        def _(*args, **kwargs):
            orig_user = env.user
            env.user = user
            try:
                return f(*args, **kwargs)
            finally:
                env.user = orig_user
        return _
    return D

def alias(from_domain, to_domain):
    @apply
    @as_user(from_domain)
    def do_alias():
        target = target_dir(domain=from_domain, version=None if '.v.' in from_domain else 'public')

        run("whoami")
        run("mkdir -p " + target)
        project_config["alias_to"] = to_domain
        domain(from_domain)
        yaml.dump(project_config, open("project_version.yaml", "w"))

        write_deploy_cfg(os.path.join(target, "project.yaml"))

def write_deploy_cfg(to_path=None):
    sync_dirs(local_dir="project_version.yaml", remote_dir=to_path or target_dir("project.yaml"))

    update_system()

def test(verbose=False):
    run(("cd %(domain_path)s && python libs/%(project_library)s/manage.py test -v " + ('2' if verbose else '1')) %
    {'domain_path': target_dir(), 'project_library': project_config['project_library']})

# Server side commands

def active_version():
    try:
        get(target_dir("project.yaml", version="public"), "/tmp/current.yaml")
    except:
        return
    else:
        current = yaml.load(open("/tmp/current.yaml"))
        return current["version"]

def update_system():
    user = env.user
    env.user = "root"
    try:
        put(os.path.join(os.path.dirname(__file__), "panconfig.py"), os.path.join("/", "usr", "bin", "panconfig.py"))
        put(os.path.join(os.path.dirname(__file__), "djangorender.py"), os.path.join("/", "usr", "lib", "python2.6", "dist-packages", "djangorender.py"))
        put(os.path.join(os.path.dirname(__file__), "httpd.conf.template"), os.path.join("/", "etc", "apache2"))

        run("panconfig.py")

        _init_d('apache2', 'reload')
    finally:
        env.user = user

# Always run once with test domain first
domain(project_config["domain"], version=project_config["version"])

