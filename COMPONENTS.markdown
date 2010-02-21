Components provide modular functionality to pandeploy.

# About Components

Each component can provide:

- Default files to add to a new project, which can be templates and
customized by the project configuration
- Default configuration settings
- Hooks to customize pandeploy commands
- Custom pandeploy commands

# Where Components Live

Components live in python packages that are importable, in the directory
pandeploy/components/ inside the package, which is *not* itself a package.

Each python module in this directory defines a global named `component`
and this is the pandeploy component that will be loaded when requested by
a user.

Components can be configured for existing projects with the `components`
key in project.yaml, defining a list of component names. The name is the
python script defining the component, without the `.py` extension. The
`pancreate` command can be given one or more -c/--component options to
associate these components at project creation time, which is also useful
to take advantage of project creation hooks by the components.

Components are expected to have unique names.

# Hooks

Components use hooks in the pandeploy operations to add and modify behavior.
This is a list of supported and planned hooks:

**Supported**

**Planned**

- **populate_new_project** to add new files to a project skeleton
- **add_to_config** to add settings related to a component
- **build**
- **deploy**
- **setup_domain**

Every hook can be used by the component by providing a method named after
the hook. The components should try not to require any order, but controls
about this will be added at some point.

Hook methods should expect one positional argument, the `project` object and
should accept `**kwargs` for any future hook-specific parameters. They do not
need to return anything.
