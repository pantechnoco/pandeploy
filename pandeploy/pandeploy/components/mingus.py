import os

class MingusComponent(object):

    def populate_new_project(self, project):
        project.add_dependency(vcs='git', url='git://github.com/montylounge/django-mingus.git', name='Mingus')

        mingus_reqs = os.path.join('ve', 'src', 'mingus', 'mingus', 'requirements.txt')
        project.install_requirements(mingus_reqs)

        os.symlink(
            os.path.join('ve', 'src', 'mingus', 'mignus', 'settings.py'),
            os.path.join(project.name, 'settings.py'))

component = MingusComponent()
