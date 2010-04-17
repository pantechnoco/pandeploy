import os
import subprocess

class Project(object):

    def setup_virtualenv(self, ve_rel='ve'):
        ve_path = os.path.join(self.path, ve_rel)
        if not os.path.exists(ve_path):
            subprocess.call(['virtualenv', '--no-site-packages', ve_rel], cwd=self.path)
            self.ve_path = ve_path


    def add_dependency(self, vcs, url, name):
        self.setup_virtualenv()
        subprocess.call(['pip', 'install', '-E', self.ve_path, '-e', '%s+%s#egg=%s' % (vcs, url, name)], cwd=self.path)

    def install_requirements(self, path='requirements.txt'):
        subprocess.call(['pip', 'install', '-E', self.ve_path, '-r', path], cwd=self.path)


    def populate_new_project(self):
        for name, component in self.components:
            component.populate_new_project(self)

    components = ()
