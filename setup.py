from setuptools import setup

dependencies = [
    'progressbar', 
    'pyvcf', 
    'markdown', 
    'sh', 
    'requests', 
    'ipython', 
]

packages = [
    'xbrowse',
    'xbrowse.analysis_modules',
    'xbrowse.annotation',
    'xbrowse.core',
    'xbrowse.coverage',
    'xbrowse.datastore',
    'xbrowse.parsers',
    'xbrowse.qc',
    'xbrowse.reference',
    'xbrowse.utils',
    'xbrowse.variant_search',
    'xbrowse.cnv',
]

setup(
    name='seqr',
    version='0.1dev',
    packages=packages,
    license='AGPL v3',
    long_description=".",
    install_requires=dependencies, 
)
