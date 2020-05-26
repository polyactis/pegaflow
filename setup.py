#!/usr/bin/env python3
import os
import sys
from setuptools import setup, find_packages

src_dir = os.path.dirname(__file__)

install_requires = []

with open(os.path.join(src_dir, 'README.md')) as readme_file:
    README = readme_file.read()

with open(os.path.join(src_dir, 'HISTORY.md')) as history_file:
    HISTORY = history_file.read()

#
# Create Manifest file to exclude tests, and service files
#
def create_manifest_file():
    f = None
    try:
        f = open('MANIFEST.in', 'w')
        #include all files in pegaflow/example
        f.write('recursive-include pegaflow/example *\n')
        f.write('global-exclude *.py[cod]\n')
    finally:
        if f:
            f.close()

def find_package_data(dirname):
    def find_paths(dirname):
        items = []
        for fname in os.listdir(dirname):
            path = os.path.join(dirname, fname)
            if os.path.isdir(path):
                items += find_paths(path)
            elif not path.endswith(".py") and not path.endswith(".pyc"):
                items.append(path)
        return items

    items = find_paths(dirname)
    return [path.replace(dirname, "") for path in items]


setup_args = dict(
    name="Pegaflow",
    version="0.1.6",
    author="Yu S. Huang",
    author_email="polyactis@gmail.com",
    description="Pegasus DAX Python API with a helper class",
    long_description_content_type="text/markdown",
    long_description=README + '\n\n' + HISTORY,
    license="Apache2",
    url="https://github.com/polyactis/pegaflow",
    python_requires=">=3.5",
    keywords=["scientific workflows"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
    ],
    packages=find_packages(exclude=['pegaflow.test*']),
    package_data={
        # If any package contains *.sh files, include them:
        "": ["*.sh", "*.md", "pegasusrc"],
    },
    include_package_data=True,
    zip_safe=False,
    scripts=['pegaflow/test/pegaflow_monitor'],
)


if __name__ == '__main__':
    create_manifest_file()
    setup(**setup_args, install_requires=install_requires)
