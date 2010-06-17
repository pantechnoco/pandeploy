__all__ = ['render_str', 'render_file']

import os, sys, types
from StringIO import StringIO
from django import template
import yaml


if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = "fakesettings"
    sys.modules["fakesettings"] = types.ModuleType("fakesettings")

    import fakesettings

    fakesettings.INSTALLED_APPS = (
        'pandeploy._djrend_tt',
    )

def render_str(template_str, **context):
    return template.Template(template_str).render(template.Context(context, autoescape=False))

def render_path(template_path, **context):
    return render_str(open(template_path).read(), **context)


def main(options, args):

    params = {}
    if options.yaml_path:
        params = yaml.load(open(options.yaml_path))
    elif options.yaml:
        params = yaml.load(StringIO(options.yaml))

    for param in options.context or ():
        name, value = param.split('=', 1)
        params[name] = value

    if options.template_path:
        print render_path(options.template_path, **params)

    if options.template_str:
        print render_str(options.template_str, **params)

if __name__ == '__main__':

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-s', '--set',
        action="append", dest="context",
        help="set a variable to be passed into the context rendering the template")
    parser.add_option('-t', '--template-str',
        action="store", dest="template_str",
        help="the contents of a template to render")
    parser.add_option('-p', '--template-path',
        action="store", dest="template_path",
        help="the path to a template to load and render")
    parser.add_option('-y', '--yaml',
        action="store", dest="yaml",
        help="sets the context from parsed yaml text")
    parser.add_option('-Y', '--yaml-path',
        action="store", dest="yaml_path",
        help="sets the context from a yaml file")

    options, args = parser.parse_args()

    main(options, args)
