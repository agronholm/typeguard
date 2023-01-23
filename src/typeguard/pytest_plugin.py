import sys

from typeguard.importhook import install_import_hook, TypeguardFinder


def pytest_addoption(parser):
    group = parser.getgroup("typeguard")
    group.addoption(
        "--typeguard-packages",
        action="store",
        help="comma separated name list of packages and modules to instrument for "
        "type checking",
    )


def pytest_configure(config):
    packages_input = config.getoption("typeguard_packages")
    if not packages_input:
        return
    elif packages_input == ".":
        _install_import_hook_for_all_modules()
    else:
        _install_import_hook_for_selected_packages(packages_input)


def _install_import_hook_for_selected_packages(packages_input):
    packages = [pkg.strip() for pkg in packages_input.split(",")]
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


def _install_import_hook_for_all_modules():
    class AllModulesFinder(TypeguardFinder):
        def should_instrument(self, module_name: str):
            return True

    install_import_hook("", cls=AllModulesFinder)
