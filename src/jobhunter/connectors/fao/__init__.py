"""FAO Jobs source connector."""

from jobhunter.connectors.fao.connector import FaoJobsConnector, FaoScanResult
from jobhunter.connectors.fao.identity import FAO_JOBS_SOURCE_ID

__all__ = [
    "FAO_JOBS_SOURCE_ID",
    "FaoJobsConnector",
    "FaoScanResult",
]
