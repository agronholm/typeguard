from typeguard.importhook import install_import_hook


def pytest_addoption(parser):
    group = parser.getgroup('typeguard')
    group.addoption('--typeguard-packages', action='store',
                    help='comma separated name list of packages and modules to instrument for '
                         'type checking')


def pytest_sessionstart(session):
    packages = session.config.getoption('typeguard_packages')
    if packages:
        package_list = [pkg.strip() for pkg in packages.split(',')]
        install_import_hook(packages=package_list)
