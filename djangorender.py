__all__ = ['render_str', 'render_file']

import os, sys, types
from django import template

if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = "fakesettings"
    sys.modules["fakesettings"] = types.ModuleType("fakesettings")

def render_str(template_str, **context):
    return template.Template(template_str).render(template.Context(context))

def render_path(template_path, **context):
    return render_str(open(template_path).read(), **context)


def main(options, args):

    params = {}
    for param in options.context:
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

    options, args = parser.parse_args()

    main(options, args)
