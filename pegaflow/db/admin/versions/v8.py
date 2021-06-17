import logging

from sqlalchemy.exc import *

from pegaflow.db.admin.admin_loader import *
from pegaflow.db.admin.versions.base_version import BaseVersion
from pegaflow.db.schema import *

DB_VERSION = 8

log = logging.getLogger(__name__)


class Version(BaseVersion):
    def __init__(self, connection):
        super().__init__(connection)

    def update(self, force=False):
        """

        :param force:
        :return:
        """
        log.info("Updating to version %s" % DB_VERSION)
        try:
            log.info("Updating master_workflowstate...")
            self.db.execute("ALTER TABLE master_workflowstate ADD reason TEXT NULL")
        except (OperationalError, ProgrammingError):
            pass
        except Exception as e:
            self.db.rollback()
            log.exception(e)
            raise Exception(e)

        self.db.commit()

    def downgrade(self, force=False):
        "Downgrade is not necessary as reason accepts NULL values"
