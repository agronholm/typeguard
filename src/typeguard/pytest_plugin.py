import sys

from typeguard import install_import_hook
from typeguard._config import global_config


def pytest_addoption(parser):
    group = parser.getgroup("typeguard")
    group.addoption(
        "--typeguard-packages",
        action="store",
        help="comma separated name list of packages and modules to instrument for "
        "type checking, or :all: to instrument all modules loaded after typeguard",
    )
    group.addoption(
        "--typeguard-debug-instrumentation",
        action="store_true",
        help="print all instrumented code to stderr",
    )


def pytest_configure(config):
    packages_option = config.getoption("typeguard_packages")
    if packages_option:
        if packages_option == ":all:":
            packages: list[str] | None = None
        else:
            packages = [pkg.strip() for pkg in packages_option.split(",")]
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

    debug_option = config.getoption("typeguard_debug_instrumentation")
    if debug_option:
        global_config.debug_instrumentation = True
