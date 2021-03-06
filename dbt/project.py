import os.path
import yaml
import pprint
import copy
import sys

default_project_cfg = {
    'source-paths': ['models'],
    'data-paths': ['data'],
    'test-paths': ['test'],
    'target-path': 'target',
    'clean-targets': ['target'],
    'outputs': {'default': {}},
    'run-target': 'default',
    'models': {},
    'model-defaults': {
        'enabled': True,
        'materialized': False
    },
    'profile': None,
    'repositories': [],
    'modules-path': 'dbt_modules'
}

default_profiles = {
    'user': {}
}

default_active_profiles = ['user']

class DbtProjectError(Exception):
    def __init__(self, message, project):
        self.project = project
        super(DbtProjectError, self).__init__(message)

class Project:

    def __init__(self, cfg, profiles, active_profile_names=[]):
        self.cfg = default_project_cfg.copy()
        self.cfg.update(cfg)
        self.profiles = default_profiles.copy()
        self.profiles.update(profiles)
        self.active_profile_names = active_profile_names

        # load profile from dbt_config.yml
        if self.cfg['profile'] is not None:
            self.active_profile_names.append(self.cfg['profile'])

        for profile_name in active_profile_names:
            if profile_name in self.profiles:
                self.cfg.update(self.profiles[profile_name])
            else:
                raise DbtProjectError("Could not find profile named '{}'".format(profile_name), self)

    def __str__(self):
        return pprint.pformat({'project': self.cfg, 'profiles': self.profiles})

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, key):
        return self.cfg.__getitem__(key)

    def __contains__(self, key):
        return self.cfg.__contains__(key)

    def __setitem__(self, key, value):
        return self.cfg.__setitem__(key, value)

    def get(self, key, default=None):
        return self.cfg.get(key, default)

    def run_environment(self):
        target_name = self.cfg['run-target']
        return self.cfg['outputs'][target_name]

    def context(self):
        target_cfg = self.run_environment()
        filtered_target = copy.deepcopy(target_cfg)
        filtered_target.pop('pass', None)
        return {'env': filtered_target}

    def with_profiles(self, profiles=[]):
        return Project(
            copy.deepcopy(self.cfg),
            copy.deepcopy(self.profiles),
            profiles)

    def validate(self):
        target_cfg = self.run_environment()
        target_name = self.cfg['run-target']

        package_name = self.cfg.get('name', None)
        package_version = self.cfg.get('version', None)

        if package_name is None or package_version is None:
            raise DbtProjectError("Project name and version is not provided", self)

        required_keys = ['host', 'user', 'pass', 'schema', 'type', 'dbname', 'port']
        for key in required_keys:
            if key not in target_cfg or len(str(target_cfg[key])) == 0:
                raise DbtProjectError("Expected project configuration '{}' was not supplied".format(key), self)

def read_profiles():
    profiles = {}
    paths = [
        os.path.join(os.path.expanduser('~'), '.dbt/profiles.yml')
    ]
    for path in paths:
        if os.path.isfile(path):
            with open(path, 'r') as f:
                m = yaml.safe_load(f)
                profiles.update(m)

    return profiles

def read_project(filename, validate=True):
    with open(filename, 'r') as f:
        project_cfg = yaml.safe_load(f)
        project_cfg['project-root'] = os.path.dirname(os.path.abspath(filename))
        profiles = read_profiles()
        proj = Project(project_cfg, profiles, default_active_profiles)

        if validate:
            proj.validate()
        return proj
