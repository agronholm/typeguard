import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import _pytest.config

from typeguard.importhook import install_import_hook


def pytest_addoption(parser: '_pytest.config.argparsing.Parser') -> None:
    group = parser.getgroup('typeguard')
    group.addoption('--typeguard-packages', action='store',
                    help='comma separated name list of packages and modules to instrument for '
                         'type checking')


def pytest_configure(config: _pytest.config.Config) -> None:
    value = config.getoption("typeguard_packages")
    if not value:
        return None

    packages = [pkg.strip() for pkg in value.split(",")]

    already_imported_packages = sorted(
        package for package in packages if package in sys.modules
    )
    if already_imported_packages:
        message = (
            "typeguard cannot check these packages because they "
            "are already imported: {}"
        )
        raise RuntimeError(message.format(", ".join(already_imported_packages)))

    install_import_hook(packages=packages)
