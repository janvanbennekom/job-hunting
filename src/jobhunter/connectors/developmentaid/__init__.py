"""DevelopmentAid Jobs source connector."""

from jobhunter.connectors.developmentaid.connector import DevelopmentAidJobsConnector
from jobhunter.connectors.developmentaid.identity import DEVELOPMENTAID_JOBS_SOURCE_ID

__all__ = ["DevelopmentAidJobsConnector", "DEVELOPMENTAID_JOBS_SOURCE_ID"]
