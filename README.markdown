# About

PanDeploy is just a collection of tools I've built to make the common things
I've got to do across a bunch of domains a bit easier. Keeping everything more
generic as a result forces a better setup that won't get me stuck down the
road.

# Requirements

- Django 1.1+ (Will install 1.2 by default when 1.2 releases)
- pyyaml
- fabric 0.9+

# pancreate

Creates a new domain project with a Django project within it. Initializes
libs, media, and apps directories. Puts the deployment scripts in place.

This is obviously the least often used, so its the least mature.

This is also slated for expansion with the introduction of Pandeploy
Components. Each component will be able to add configuration and parts
to a project, allowing more to be handled automatically and optionally.
For example, the Django support will eventually be in an optional component,
as well as the apache config generation, which would allow other webserver
support.

Each component can provide:

- Default files to add to a new project, which can be templates and
customized by the project configuration
- Default configuration settings
- Hooks to customize pandeploy commands
- Custom pandeploy commands


# pandeploy.py

At the heart, this is a library that the generated fabfile.py in every
created project imports commands from. You can add commands to the fabfile,
but you always can depend on an updated, consistent set of commands here.

All python packages, including the main project, all applications and
libraries, are synced to /domains/[domainname]/libs/, which is in the path.
Data and media are uploaded, as well. The django settings.py and manage.py
are automatically generated from the project.yaml file.

# project.yaml

In every project, this configuration file sets up everything. The contents
are parsed as YAML, and an optional project_extends.yaml file (usually a
symlink) is loaded as defaults.

**DEBUG** enables debug mode.

**apache_order** is an integer value to control the order of domains
in the generated httpd.conf. This will become apache.domain_order soon.

**domain** is the domain being deployed to

**project_library** is the name of the Django project

**hosts** is a list of servers to deploy to. This should/will default to
the domain name.

**static** maps static URLs to static directories to serve. Apache is
configured to serve all directories listed here. Ex:

    static:
     - path: static/media/css
       url: css
     - path: static/robots.txt
       url: robots.txt

everything else is passed to django.

**wsgi** configures mod_wsgi, but only supports a **processes** entry, yet.

**django** contains all django-specific settings

 * **middleware** is a list of Django middleware to configure.
 * **database** configures the database for Django, and supports **engine** as
   sqlite3 right now. The rest of the fields will be added for non-sqlite3.
 * **extra_settings** allows for arbitrary values to be set in the
   final settings module.

**email**

 * **host** smtp.yourmailserver.com
 * **port** 587
 * **tls** true
 * **username** "username"
 * **password** "******"

# Server Layout

NOTE: Differs from reality. This is what I'll be changing it to.

**/domains/** contains all the actively hosted domains.

**/domains/domainname.tld/** contains all the current versions of a domain. 

**/domains/domainname.tld/version-x.y.z/** contains all the content and scripts for a version of the domain.

**/domains/domainname.tld/version-current/** is a symlink to the current version.

**/domains/domainname.tld/top-level/** is the actual domain. It is configured to alias to the current version.
