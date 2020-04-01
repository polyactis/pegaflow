# Pegasus Workflow Management System Python3 API
Pegaflow is a package of the Python3 APIs for Pegasus WMS (http://pegasus.isi.edu/). Pegasus(<5.0) offers Python2 support only. Pegasus allows a developer to connect dependent computing jobs into a DAG (Directed Acyclic Graph) and run jobs according to the dependency.

[Workflow.py](pegaflow/Workflow.py) is the key difference from the official Pegasus Python APIs. Inheriting Workflow.py, users can write Pegasus workflows in an Object-Oriented way. It significantly reduces the amount of coding in writing a Pegasus workflow.

Pegasus jobs do NOT support UNIX pipes while many UNIX programs can only output to stdout. A shell wrapper, [pegaflow/shell/pipeCommandOutput2File.sh](pegaflow/shell/pipeCommandOutput2File.sh), is offered to redirect the output (stdout) of a program to a file. [pegaflow/shell/]([pegaflow/shell/) contains a few other useful shell scripts.

* The DAX API (v3) and the helper class Workflow.py
* The monitoring API
* The Stampede database API
* The Pegasus statistics API
* The Pegasus plots API
* Miscellaneous Pegasus utilities
* The Pegasus service, including the ensemble manager and dashboard

This package's source code is adapted from https://github.com/pegasus-isi/pegasus, version 4.9.1,


# Installation
Prerequisites:

* Pegasus https://github.com/pegasus-isi/pegasus
* HTCondor https://research.cs.wisc.edu/htcondor/, the underlying job scheduler.

Install pegaflow:

```python
pip3 install pegaflow
```

If a user intends to use Non-DAX Pegasus APIs, the following Python packages need to be installed as well.

* "Werkzeug==0.14.1",
* "Flask==0.12.4",
* "Jinja2==2.8.1",
* "SQLAlchemy",
* "Flask-Cache==0.13.1",
* "requests==2.18.4",
* "MarkupSafe==1.0",
* "boto==2.48.0",
* "pam==0.1.4",
* "plex==2.0.0dev",
* "future"

# Examples

Check [pegaflow/example/](pegaflow/example/) for examples how to inherit [Workflow.py](pegaflow/Workflow.py) and run Pegasus workflows.
