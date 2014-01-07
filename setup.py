from distutils.core import setup

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
]

setup(
    name='xBrowse',
    version='0.1dev',
    packages=packages,
    license='AGPL v3',
    long_description=".",
)