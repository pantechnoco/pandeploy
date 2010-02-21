import os

class MingusComponent(object):

    def populate_new_project(self, project):
        project.add_dependency(vcs='git', url='git://github.com/montylounge/django-mingus.git', name='Mingus')

component = MingusComponent()
