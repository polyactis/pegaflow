import json
import os
import re
from datetime import datetime
from enum import Enum

from flask import url_for
from sqlalchemy import sql
from sqlalchemy.orm.exc import NoResultFound

# TODO: circular import here...
import pegaflow.db as db
from pegaflow import user


def timestamp(dt):
    return (dt - datetime(1970, 1, 1)).total_seconds()


class EMError(Exception):
    def __init__(self, message, status_code=500):
        Exception.__init__(self, message)
        self.status_code = status_code


def validate_ensemble_name(name):
    if name is None:
        raise EMError("Specify ensemble name")
    if len(name) >= 100:
        raise EMError("Ensemble name too long: %d" % len(name))
    if re.match(r"\A[a-zA-Z0-9_-]+\Z", name) is None:
        raise EMError("Invalid ensemble name: %s" % name)
    return name


def validate_priority(priority):
    try:
        return int(priority)
    except ValueError:
        raise EMError("Invalid priority: %s" % priority)


class EnsembleBase:
    def set_name(self, name):
        self.name = validate_ensemble_name(name)

    def set_created(self):
        self.created = datetime.utcnow()

    def set_updated(self):
        self.updated = datetime.utcnow()


class States(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


EnsembleStates = States(["ACTIVE", "HELD", "PAUSED"])
EnsembleWorkflowStates = States(
    [
        "READY",
        "PLANNING",
        "PLAN_FAILED",
        "QUEUED",
        "RUN_FAILED",
        "RUNNING",
        "FAILED",
        "SUCCESSFUL",
        "ABORTED",
    ]
)


class Ensemble(EnsembleBase):
    def __init__(self, username, name):
        self.username = username
        self.set_name(name)
        self.set_created()
        self.set_updated()
        self.state = EnsembleStates.ACTIVE
        self.set_max_running(1)
        self.set_max_planning(1)

    def set_state(self, state):
        state = state.upper()
        if state not in EnsembleStates:
            raise EMError("Invalid ensemble state: %s" % state)
        self.state = state

    def set_max_running(self, max_running):
        try:
            max_running = int(max_running)
            if max_running < 1:
                raise EMError("Value for max_running must be >= 1: %s" % max_running)
            self.max_running = max_running
        except ValueError:
            raise EMError("Invalid value for max_running: %s" % max_running)

    def set_max_planning(self, max_planning):
        try:
            max_planning = int(max_planning)
            if max_planning < 1:
                raise EMError("Value for max_planning must be >= 1: %s" % max_planning)
            self.max_planning = max_planning
        except ValueError:
            raise EMError("Invalid value for max_planning: %s" % max_planning)

    def get_localdir(self):
        u = user.get_user_by_username(self.username)
        edir = u.get_ensembles_dir()
        return os.path.join(edir, self.name)

    def get_object(self):
        return {
            "id": self.id,
            "name": self.name,
            "created": timestamp(self.created),
            "updated": timestamp(self.updated),
            "state": self.state,
            "max_running": self.max_running,
            "max_planning": self.max_planning,
            "workflows": url_for(
                "route_list_ensemble_workflows", name=self.name, _external=True
            ),
            "href": url_for("route_get_ensemble", name=self.name, _external=True),
        }


class EnsembleWorkflow(EnsembleBase):
    def __init__(self, ensemble_id, name, basedir, plan_command):
        self.ensemble_id = ensemble_id
        self.set_name(name)
        self.set_basedir(basedir)
        self.set_created()
        self.set_updated()
        self.state = EnsembleWorkflowStates.READY
        self.set_priority(0)
        self.set_plan_command(plan_command)
        self.set_wf_uuid(None)
        self.set_submitdir(None)

    def set_state(self, state):
        state = state.upper()
        if state not in EnsembleWorkflowStates:
            raise EMError("Invalid ensemble workflow state: %s" % state)
        self.state = state

    def change_state(self, state):
        # The allowed transitions are:
        #   PLAN_FAILED -> READY
        #   RUN_FAILED -> QUEUED
        #   RUN_FAILED -> READY
        #   FAILED -> QUEUED
        #   FAILED -> READY
        if self.state == EnsembleWorkflowStates.PLAN_FAILED:
            if state != EnsembleWorkflowStates.READY:
                raise EMError("Can only replan workflows in PLAN_FAILED state")
        elif self.state == EnsembleWorkflowStates.RUN_FAILED:
            if state not in (
                EnsembleWorkflowStates.READY,
                EnsembleWorkflowStates.QUEUED,
            ):
                raise EMError("Can only replan or rerun workflows in RUN_FAILED state")
        elif self.state == EnsembleWorkflowStates.FAILED:
            if state not in (
                EnsembleWorkflowStates.READY,
                EnsembleWorkflowStates.QUEUED,
            ):
                raise EMError("Can only replan or rerun workflows in FAILED state")
        else:
            raise EMError("Invalid state change: {} -> {}".format(self.state, state))

        self.set_state(state)

    def set_priority(self, priority):
        self.priority = validate_priority(priority)

    def set_wf_uuid(self, wf_uuid):
        if wf_uuid is not None and len(wf_uuid) != 36:
            raise EMError("Invalid wf_uuid")
        self.wf_uuid = wf_uuid

    def set_basedir(self, basedir):
        self.basedir = basedir

    def set_submitdir(self, submitdir):
        self.submitdir = submitdir

    def set_plan_command(self, plan_command):
        self.plan_command = plan_command

    def _get_file(self, suffix):
        edir = self.ensemble.get_localdir()
        wf = self.name
        filename = "{}.{}".format(wf, suffix)
        return os.path.join(edir, filename)

    def get_basedir(self):
        return self.basedir

    def get_pidfile(self):
        return self._get_file("plan.pid")

    def get_resultfile(self):
        return self._get_file("plan.result")

    def get_runfile(self):
        return self._get_file("plan.run")

    def get_logfile(self):
        return self._get_file("log")

    def get_plan_command(self):
        return self.plan_command

    def get_object(self):
        return {
            "id": self.id,
            "name": self.name,
            "created": timestamp(self.created),
            "updated": timestamp(self.updated),
            "state": self.state,
            "priority": self.priority,
            "wf_uuid": self.wf_uuid,
            "href": url_for(
                "route_get_ensemble_workflow",
                ensemble=self.ensemble.name,
                workflow=self.name,
                _external=True,
            ),
        }

    def get_detail_object(self):
        o = self.get_object()
        o["basedir"] = self.basedir
        o["plan_command"] = self.plan_command
        o["log"] = self.get_logfile()
        o["submitdir"] = self.submitdir
        return o


class Ensembles:
    def __init__(self, session):
        self.session = session

    def list_ensembles(self, username):
        q = self.session.query(Ensemble)
        q = q.filter(Ensemble.username == username)
        q = q.order_by(Ensemble.created)
        return q.all()

    def list_actionable_ensembles(self):
        states = (
            EnsembleWorkflowStates.READY,
            EnsembleWorkflowStates.PLANNING,
            EnsembleWorkflowStates.QUEUED,
            EnsembleWorkflowStates.RUNNING,
        )
        stmt = (
            sql.exists()
            .where(Ensemble.id == EnsembleWorkflow.ensemble_id)
            .where(EnsembleWorkflow.state.in_(states))
        )
        return self.session.query(Ensemble).filter(stmt).all()

    def get_ensemble(self, username, name):
        try:
            return (
                self.session.query(Ensemble)
                .filter(Ensemble.username == username, Ensemble.name == name)
                .one()
            )
        except NoResultFound:
            raise EMError("No such ensemble: %s" % name, 404)

    def get_ensemble_name(self, ensemble_id: int):
        """Given an ensemble id, get its name

        :param ensemble_id: id of target ensemble
        :type ensemble_id: int
        :return: name of target ensemble
        :rtype: str
        """
        return self.session.query(Ensemble).filter_by(id=ensemble_id).first().name

    def create_ensemble(self, username, name, max_running, max_planning):
        if (
            self.session.query(Ensemble)
            .filter(Ensemble.username == username, Ensemble.name == name)
            .count()
            > 0
        ):
            raise EMError("Ensemble %s already exists" % name, 400)

        ensemble = Ensemble(username, name)
        ensemble.set_max_running(max_running)
        ensemble.set_max_planning(max_planning)
        self.session.add(ensemble)
        self.session.flush()
        return ensemble

    def list_ensemble_workflows(self, ensemble_id):
        q = self.session.query(EnsembleWorkflow)
        q = q.filter(EnsembleWorkflow.ensemble_id == ensemble_id)
        q = q.order_by(EnsembleWorkflow.created)
        return q.all()

    def get_ensemble_workflow(self, ensemble_id, name):
        try:
            q = self.session.query(EnsembleWorkflow)
            q = q.filter(
                EnsembleWorkflow.ensemble_id == ensemble_id,
                EnsembleWorkflow.name == name,
            )
            return q.one()
        except NoResultFound:
            raise EMError("No such ensemble workflow: %s" % name, 404)

    def create_ensemble_workflow(
        self, ensemble_id, name, basedir, priority, plan_command
    ):

        # Verify that the workflow doesn't already exist
        q = self.session.query(EnsembleWorkflow)
        q = q.filter(
            EnsembleWorkflow.ensemble_id == ensemble_id, EnsembleWorkflow.name == name
        )
        if q.count() > 0:
            raise EMError("Ensemble workflow %s already exists" % name, 400)

        # Create database record
        w = EnsembleWorkflow(ensemble_id, name, basedir, plan_command)
        w.set_priority(priority)
        self.session.add(w)
        self.session.flush()

        return w

    def write_planning_script(
        self,
        f,
        basedir,
        bundledir,
        dax,
        sites,
        output_site,
        staging_sites=None,
        clustering=None,
        force=False,
        cleanup=None,
    ):

        f.write("#!/bin/bash\n")
        f.write("pegasus-plan \\\n")

        # We need to make sure that the dashboard info is
        # sent to the same database we are using
        f.write("-Dpegasus.dashboard.output=%s \\\n" % self.dburi)

        f.write("--conf pegasus.properties \\\n")
        f.write("--site %s \\\n" % ",".join(sites))
        f.write("--output-site %s \\\n" % output_site)

        if staging_sites is not None and len(staging_sites) > 0:
            pairs = ["{}={}".format(k, v) for k, v in staging_sites.items()]
            f.write("--staging-site %s \\\n" % ",".join(pairs))

        if clustering is not None and len(clustering) > 0:
            f.write("--cluster %s \\\n" % ",".join(clustering))

        if force:
            f.write("--force \\\n")

        if cleanup is not None:
            f.write("--cleanup %s \\\n" % cleanup)

        f.write("--dir %s \\\n" % os.path.join(basedir, "submit"))
        f.write("--dax %s \\\n" % os.path.join(bundledir, dax))
        f.write("--input-dir %s \n" % bundledir)

        f.write("exit $?")


# --- workflow trigger ---------------------------------------------------------
TriggerStates = States(["READY", "RUNNING", "FAILED", "STOPPED"])


class TriggerType(Enum):
    """Supported trigger types"""

    CRON = "CRON"
    FILE_PATTERN = "FILE_PATTERN"


class Triggers:
    """Trigger table data access object"""

    def __init__(self, session):
        self.session = session

    def get_trigger(self, ensemble_id: int, trigger_name: str):
        """Get a specific trigger

        :param ensemble_id: id of the nsemble that the trigger belongs to
        :type ensemble_id: int
        :param trigger_name: name of the trigger
        :type trigger_name: str
        """
        try:
            return (
                self.session.query(db.schema.Trigger)
                .filter_by(ensemble_id=ensemble_id, name=trigger_name)
                .one()
            )
        except NoResultFound:
            raise EMError(
                "No such trigger: {} assigned to ensemble id: {}".format(
                    trigger_name, ensemble_id
                ),
                status_code=404,
            )

    def list_triggers(self):
        """List all triggers"""
        return self.session.query(db.schema.Trigger).all()

    def list_triggers_by_ensemble(self, username: str, ensemble: str):
        """List all triggers belonging to a specific ensemble

        :param username: name of user making request
        :type username: str
        :param ensemble: ensemble name
        :type ensemble: str
        :return: list of Triggers
        :rtype: List[Trigger]
        """
        q = self.session.query(db.schema.Trigger).filter(
            Ensemble.username == username,
            Ensemble.name == ensemble,
            Ensemble.id == Trigger.ensemble_id,
        )

        return q.all()

    def insert_trigger(
        self,
        ensemble_id: int,
        trigger: str,
        trigger_type: str,
        workflow_script: str,
        workflow_args: str,
        **trigger_kwargs
    ):
        """Insert a trigger

        :param ensemble_id: the id of the ensemble this trigger belongs to
        :type ensemble_id: int
        :param trigger: name of the trigger
        :type trigger: str
        :param trigger_type: the type of the trigger (e.g. CRON, FILE_PATTERN, etc.)
        :type trigger_type: str
        :param workflow_script: the workflow generator & planning script
        :type workflow_script: str
        :param workflow_args: any command line args to be pass to the workflow_script
        :type workflow_args: str
        :param trigger_kwargs: any arguments specific to the trigger (e.g. interval=10s)
        """

        self.session.add(
            db.schema.Trigger(
                ensemble_id=ensemble_id,
                name=trigger,
                state="READY",
                workflow=json.dumps({"script": workflow_script, "args": workflow_args}),
                args=json.dumps(trigger_kwargs),
                _type=trigger_type,
            )
        )

        self.session.commit()

    def update_state(self, ensemble_id: int, trigger_id: int, new_state: str):
        """Update the state of a trigger

        :param ensemble_id: id of the ensemble to which the trigger belongs
        :type ensemble_id: int
        :param trigger_id: id of the trigger
        :type trigger_id: int
        :param new_state: the new state the trigger will be updated to
        :type new_state: str
        """

        self.session.query(db.schema.Trigger).filter_by(
            ensemble_id=ensemble_id, _id=trigger_id
        ).update({"state": new_state})

        self.session.commit()

    def delete_trigger(self, ensemble_id: int, trigger: str):
        """Delete a trigger from the database

        :param ensemble_id: id of the ensemble to which the trigger belongs
        :type ensemble: int
        :param trigger: name of the trigger
        :type trigger: str
        """

        self.session.query(db.schema.Trigger).filter_by(
            ensemble_id=ensemble_id, name=trigger
        ).delete()

        self.session.commit()

    @staticmethod
    def get_object(trigger):
        """Get trigger as dict"""

        return {
            "id": trigger._id,
            "ensemble_id": trigger.ensemble_id,
            "name": trigger.name,
            "state": trigger.state,
            "workflow": json.loads(trigger.workflow),
            "args": json.loads(trigger.args),
            "type": trigger._type,
        }
