- [1. Pegasus Workflow Management System Python3 API](#1-pegasus-workflow-management-system-python3-api)
- [2. Installation](#2-installation)
- [3. Examples](#3-examples)

# 1. Pegasus Workflow Management System Python3 API

Pegaflow, https://github.com/polyactis/pegaflow, is a package of the Python3 APIs for Pegasus WMS (http://pegasus.isi.edu/). Pegasus(version<5.0) offers Python2 support only. Pegasus allows a developer to connect dependent computing jobs into a DAG (Directed Acyclic Graph) and run jobs according to the dependency.

[Workflow.py](pegaflow/Workflow.py) is the key difference from the official Pegasus Python APIs. Inheriting [Workflow.py](pegaflow/Workflow.py), users can write Pegasus workflows in an Object-Oriented way. It significantly reduces the amount of coding in writing a Pegasus workflow.

Pegasus jobs do NOT support UNIX pipes while many UNIX programs can only output to stdout. A shell wrapper, [pegaflow/tools/pipe2File.sh](pegaflow/tools/pipe2File.sh), is offered to redirect the output (stdout) of a program to a file. [pegaflow/tools/](pegaflow/tools/) contains a few other useful shell scripts.

- The DAX API (v3) and the helper class Workflow.py
- The monitoring API
- The Stampede database API
- The Pegasus statistics API
- The Pegasus plots API
- Miscellaneous Pegasus utilities
- The Pegasus service, including the ensemble manager and dashboard

This package's source code is adapted from https://github.com/pegasus-isi/pegasus, version 4.9.1,

# 2. Installation

Install pegaflow:

```python
pip3 install --upgrade pegaflow
```

Pegasus and HTCondor (Condor) are only required on computers where you intend to submit and run workflows.

On computers where only DAXs (DAG XML files) are outputted, no need to install Pegasus and Condor.

- Pegasus https://github.com/pegasus-isi/pegasus
- HTCondor https://research.cs.wisc.edu/htcondor/, the underlying job scheduler.

If a user intends to use Non-DAX Pegasus APIs, the following Python packages need to be installed as well.

- "Werkzeug==0.14.1",
- "Flask==0.12.4",
- "Jinja2==2.8.1",
- "SQLAlchemy",
- "Flask-Cache==0.13.1",
- "requests==2.18.4",
- "MarkupSafe==1.0",
- "boto==2.48.0",
- "pam==0.1.4",
- "plex==2.0.0dev",
- "future"

# 3. Examples

Check [pegaflow/example/](pegaflow/example/) for examples.

- [pegaflow/example/WordCountFiles.py](pegaflow/example/WordCountFiles.py) is an example that inherits [Workflow.py](pegaflow/Workflow.py). Users should be familiar with Object-Oriented programming.
- [pegaflow/example/WCFiles_Function.py](pegaflow/example/WCFiles_Function.py) is a procedural-programming example that invokes functions in [Workflow.py](pegaflow/Workflow.py).
