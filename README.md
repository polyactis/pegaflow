# Pegasus Workflow Management System Python3 API
Pegaflow is a package of the Python(2&3) APIs for Pegasus WMS (http://pegasus.isi.edu/). Pegasus offers Python2 support only. Pegasus allows a developer to connect dependent computing jobs into a DAG (Directed Acyclic Graph) and run jobs according to the dependency.

Pegaflow also contains a helper class, Workflow.py, for users to inherit. It simplifies the Pegasus workflow writing.

Pegasus jobs do NOT support UNIX pipes. [pegaflow/shell/pipeCommandOutput2File.sh](pegaflow/shell/pipeCommandOutput2File.sh) is offered to redirect the output (stdout) of a program to a file. shell/ contains a few other useful shell scripts.

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
* HTCondor https://research.cs.wisc.edu/htcondor/, if multi-node execution is intended.

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

Check [pegaflow/example/README.md](pegaflow/example/README.md).