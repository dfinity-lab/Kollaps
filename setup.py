
from setuptools import setup

setup(name='need',
      version='2.0',
      description='Decentralized network emulator',
      url='https://github.com/miguelammatos/NEED.git',
      author='Joao Neves, Paulo Gouveia, Luca Liechti',
      packages=[
          'need',
          'need.NEEDlib.deploymentGenerators',
          'need.NEEDlib.bootstrapping',
          'need.NEEDlib.communications',
          'need.NEEDlib.NEEDDomainLanguage',
          'need.NEEDlib',
          'need.TCAL',
          'need.shm'
      ],
      install_requires=[
          'dnspython',
          'docker',
          'kubernetes',
          'netifaces'
      ],
      include_package_data=True,
      package_data={
          'need.TCAL': ['libTCAL.so'],
          'need': ['static/css/*', 'static/js/*',  'templates/*.html'],
          'need.shm': ['EnforcerSharedMem.so', 'ManagerSharedMem.so'],
      },
      entry_points={
          'console_scripts': ['NEEDdeploymentGenerator=need.deploymentGenerator:main',
                              'NEEDDashboard=need.Dashboard:main',
                              'NEEDLogger=need.Logger:main',
                              'EmulationManager=need.EmulationManager:main',
                              'EmulationEnforcer=need.EmulationEnforcer:main',
                              'NEEDbootstrapper=need.bootstrapper:main',
                              'NDLTranslator=need.NDLTranslator:main'],
      },
      zip_safe=False)
