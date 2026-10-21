"""SQLAlchemy models, one module per owning domain (table prefix = module).

Every model is re-exported here, so `from app.models import KadiCase` keeps working and
importing this package registers every table on `Base.metadata` (Alembic, create_all).
"""

from app.models.kadi import (  # noqa: F401
    KadiCase,
    KadiEntity,
    KadiCaseDocument,
    KadiDocumentJob,
    KadiResolutionDecision,
    KadiThresholdCalibration,
    KadiModuleInsight,
    kadi_case_entities,
)
from app.models.schemesetu import (  # noqa: F401
    SchemeSetuCaseProfile,
)
from app.models.dawacheck import (  # noqa: F401
    DawaCheckGenericMapping,
)
from app.models.bimanyay import (  # noqa: F401
    BimaNyayCase,
    BimaNyayGrievance,
    BimaNyayTimelineEvent,
)
from app.models.billnyay import (  # noqa: F401
    BillNyayAppeal,
)
from app.models.daavisetu import (  # noqa: F401
    DaaviSetuClaim,
    DaaviSetuInstitution,
    DaaviSetuPlaybook,
)
from app.models.clinical_review import (  # noqa: F401
    KadiClinicalReviewer,
    KadiClinicalReview,
    KadiClinicalStatement,
    KadiClinicalFactConfirmation,
    KadiClinicalAuditEvent,
)
from app.models.safety import (  # noqa: F401
    KadiSafetyRule,
    KadiSafetyRuleApproval,
    KadiSafetyScanResult,
)
from app.models.transcription import (  # noqa: F401
    KadiTranscriptionTask,
    KadiTranscriptionAssignment,
    KadiTranscriptionSubmission,
)

__all__ = [
    "KadiCase",
    "KadiEntity",
    "KadiCaseDocument",
    "KadiDocumentJob",
    "KadiResolutionDecision",
    "KadiThresholdCalibration",
    "KadiModuleInsight",
    "kadi_case_entities",
    "SchemeSetuCaseProfile",
    "DawaCheckGenericMapping",
    "BimaNyayCase",
    "BimaNyayGrievance",
    "BimaNyayTimelineEvent",
    "BillNyayAppeal",
    "DaaviSetuClaim",
    "DaaviSetuInstitution",
    "DaaviSetuPlaybook",
    "KadiClinicalReviewer",
    "KadiClinicalReview",
    "KadiClinicalStatement",
    "KadiClinicalFactConfirmation",
    "KadiClinicalAuditEvent",
    "KadiSafetyRule",
    "KadiSafetyRuleApproval",
    "KadiSafetyScanResult",
    "KadiTranscriptionTask",
    "KadiTranscriptionAssignment",
    "KadiTranscriptionSubmission",
]
