import os
import sys


class ComponentLoader(object):

    def __init__(self):
        self.components = {}

    def _find_component_libraries(self):
        for path in sys.path:
            if not os.path.isdir(path):
                continue

            for package_name in os.listdir(path):
                package_path = os.path.join(path, package_name)
                if os.path.isdir(package_path) and 'pandeploy' in os.listdir(package_path):
                    if 'components' in os.listdir(os.path.join(package_path, 'pandeploy')):
                        yield package_path

    def _components_from_library(self, path):
        components_dir = os.path.join(path, 'pandeploy', 'components')
        for component_file in os.listdir(components_dir):
            if component_file.endswith('.py'):
                component_globals = {}
                execfile(os.path.join(components_dir, component_file), component_globals)
                try:
                    yield component_globals['component']
                except KeyError:
                    pass

    def load_all(self):
        for CL in self._find_component_libraries():
            for C in self._components_from_library(CL):
                yield C
