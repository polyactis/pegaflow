# Pegasus Workflow Management System Python3 API
Pegapy3 contains the Python3 APIs for Pegasus WMS (http://pegasus.isi.edu/). Pegasus only offers Python2 support.

Pegapy3 also contains a helper class, Workflow.py, for users to inherit. It simplifies the Pegasus workflow writing.

Pegasus allows a developer to connect dependent computing jobs into a DAG (Directed Acyclic Graph) and starts jobs according to the dependency.

* The DAX API (Versions 3) and the helper class Workflow.py
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

Install pegapy3:

```python
pip3 install pegapy3
```

If the user intends to use functions beyond the DAX APIs, he/she should install the following Python packages as well.

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

Check [pegapy3/example/README.md](pegapy3/example/README.md).