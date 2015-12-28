import os.path

from setuptools import setup

here = os.path.dirname(__file__)
readme_path = os.path.join(here, 'README.rst')
readme = open(readme_path).read()

setup(
    name='typeguard',
    use_scm_version={
        'local_scheme': 'dirty-tag'
    },
    description='Run-time type checker for Python',
    long_description=readme,
    author='Alex Grönholm',
    author_email='alex.gronholm@nextday.fi',
    url='https://github.com/agronholm/typeguard',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    license='MIT',
    zip_safe=True,
    py_modules=['typeguard'],
    setup_requires=[
        'setuptools_scm >= 1.7.0'
    ],
    extras_require={
        ':python_version == "3.2"': 'typing >= 3.5',
        ':python_version == "3.3"': 'typing >= 3.5',
        ':python_version == "3.4"': 'typing >= 3.5'
    }
)
