from setuptools import setup, find_packages

setup(
    name='kuro',
    description='Package for managing machine learning experiments',
    url='https://github.com/EntilZha/kuro',
    author='Pedro Rodriguez',
    license='Apache V2',
    version='0.1.0',
    install_requires=[
        'django~=2.0.1',
        'djangorestframework',
        'jsonfield',
        'coreapi', 'coreapi-cli',
        'py-cpuinfo', 'psutil', 'gpustat',
        'numpy',
        'dash==0.20.0',
        'dash-renderer==0.11.2',
        'dash-html-components==0.8.0',
        'dash-core-components==0.18.0',
        'plotly'
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'test*'])
)