import sys
import setuptools
import pathlib

install_requires = []
tests_require = ["pytest", "pytest-cov", "pytest-flake8"]
dev_requires = install_requires + tests_require + ["documenteer[pipelines]"]
scm_version_template = """# Generated by setuptools_scm
__all__ = ["__version__"]

__version__ = "{version}"
"""
tools_path = pathlib.Path(setuptools.__path__[0])
base_prefix = pathlib.Path(sys.base_prefix)
data_files_path = tools_path.relative_to(base_prefix).parents[1]

setuptools.setup(
    name="ts-authorize",
    description="Service to handle SAL authorization requests",
    use_scm_version={
        "write_to": "python/lsst/ts/authorize/version.py",
        "write_to_template": scm_version_template,
    },
    setup_requires=["setuptools_scm", "pytest-runner"],
    install_requires=install_requires,
    package_dir={"": "python"},
    packages=setuptools.find_namespace_packages(where="python"),
    package_data={"": ["*.rst", "*.yaml"]},
    scripts=["bin/request_authorization.py", "bin/run_authorization_service.py"],
    tests_require=tests_require,
    extras_require={"dev": dev_requires},
    license="GPL",
    project_urls={
        "Bug Tracker": "https://jira.lsstcorp.org/secure/Dashboard.jspa",
        "Source Code": "https://github.com/lsst-ts/ts_authorize",
    },
)
