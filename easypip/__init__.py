from enum import Enum
from functools import cache
import json
import subprocess
from typing import List
from pkg_resources import Requirement, parse_requirements
from packaging.version import parse as parse_version
import sys
import importlib
import logging


class IPython(Enum):
    NONE = 0
    OTHER = 1
    IPYTHON = 2
    JUPYTER = 3
    GOOGLE_COLAB = 4


@cache
def ipython():
    """Returns true if running in google Colab"""
    try:
        shell = get_ipython().__class__.__module__
        if shell is None:
            return IPython.NONE

        return {
            "IPython.terminal.interactiveshell": IPython.IPYTHON,
            "ipykernel.zmqshell": IPython.JUPYTER,
            "google.colab._shell": IPython.GOOGLE_COLAB,
        }.get(shell, IPython.OTHER)

    except NameError:
        return IPython.NONE


def is_notebook():
    """Returns true if running in a notebook"""
    return ipython() != IPython.NONE


class Installer:
    _packages = None

    @staticmethod
    def packages():
        if Installer._packages is None:
            Installer._packages = {}
            for p in json.loads(
                subprocess.check_output(
                    [sys.executable, "-m", "pip", "list", "--format", "json"]
                ).decode()
            ):
                Installer._packages[p["name"].lower()] = p
        return Installer._packages

    @staticmethod
    def has_requirement(requirement: Requirement):
        """Returns true if the requirement is fulfilled"""
        package = Installer.packages().get(requirement.project_name.lower(), None)

        if package is None:
            return False

        for comparator, desired_version in requirement.specs:
            desired_version = parse_version(desired_version)

            version = parse_version(package["version"])
            if comparator == "<=":
                return version <= desired_version
            elif comparator == ">=":
                return version >= desired_version
            elif comparator == "==":
                return version == desired_version
            elif comparator == ">":
                return version > desired_version
            elif comparator == "<":
                return version < desired_version

        return True

    @staticmethod
    def install(requirement: Requirement, extra_args: List[str] = []):
        logging.info("Installing %s", requirement)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", str(requirement)] + extra_args
        )
        Installer._packages = None


def easyimport(spec: str, ask=False):
    reqs = [req for req in parse_requirements(spec)]
    assert len(reqs) == 1, "only one package should be mentioned in the specification"
    (req,) = reqs

    if not Installer.has_requirement(req):
        if ask:
            answer = ""
            while answer not in ["y", "n"]:
                answer = input(
                    f"Module is not installed. Install {spec}? [y/n] "
                ).lower()

        if not ask or answer == "y":
            Installer.install(req)
        else:
            logging.warning("Not installing as required")
            return None

    return importlib.import_module(req.name)


has_requirement = Installer.has_requirement
install = Installer.install
