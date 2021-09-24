import codecs
from setuptools import setup, find_packages

entry_points = {
    "z3c.autoinclude.plugin": [
        'target = nti.app',
    ],
    'console_scripts': [
        "nti_library_renderer = nti.app.contentlibrary_rendering.scripts.nti_library_renderer:main",
    ]
}


TESTS_REQUIRE = [
    'nti.app.products.ou',
    'nti.app.testing',
    'nti.testing',
    'zope.testrunner',
]


def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()


setup(
    name='nti.app.contentlibrary_rendering',
    version=_read('version.txt').strip(),
    author='Jason Madden',
    author_email='jason@nextthought.com',
    description="Application layer content library rendering",
    long_description=_read('README.rst'),
    license='Apache',
    keywords='pyramid content library rendering',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython'
    ],
    url="https://github.com/NextThought/nti.app.contentlibrary_rendering",
    zip_safe=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    namespace_packages=['nti', 'nti.app'],
    tests_require=TESTS_REQUIRE,
    install_requires=[
        'setuptools',
        'docutils',
        'nti.app.asynchronous',
        'nti.app.contentlibrary',
        'nti.assessment',
        'nti.base',
        'nti.common',
        'nti.contentlibrary',
        'nti.contentlibrary_rendering',
        'nti.contentrendering',
        'nti.contentrendering_assessment',
        'nti.contenttypes.presentation',
        'nti.externalization',
        'nti.links',
        'nti.metadata',
        'nti.ntiids',
        'nti.publishing',
        'nti.site',
        'pyramid',
        'requests',
        'z3c.autoinclude',
        'zc.intid',
        'zope.cachedescriptors',
        'zope.component',
        'zope.generations',
        'zope.interface',
        'zope.intid',
        'zope.location',
        'zope.security',
    ],
    extras_require={
        'test': TESTS_REQUIRE,
        'docs': [
            'Sphinx',
            'repoze.sphinx.autointerface',
            'sphinx_rtd_theme',
        ],
    },
    entry_points=entry_points,
)
