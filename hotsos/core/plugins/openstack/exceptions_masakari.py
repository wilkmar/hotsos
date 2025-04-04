
# sed -rn 's/^class\s+(\S+)\(.+/    "\1",/p' masakari/exception.py
MASAKARI_EXCEPTIONS = [
    "ConvertedException",
    "MasakariException",
    "APIException",
    "APITimeout",
    "Conflict",
    "Invalid",
    "InvalidName",
    "InvalidInput",
    "InvalidAPIVersionString",
    "MalformedRequestBody",
    "NotFound",
    "ConfigNotFound",
    "Forbidden",
    "AdminRequired",
    "PolicyNotAuthorized",
    "PasteAppNotFound",
    "InvalidContentType",
    "VersionNotFoundForAPIMethod",
    "InvalidGlobalAPIVersion",
    "ApiVersionsIntersect",
    "ValidationError",
    "InvalidSortKey",
    "MarkerNotFound",
    "FailoverSegmentNotFound",
    "HostNotFound",
    "NotificationNotFound",
    "FailoverSegmentNotFoundByName",
    "HostNotFoundByName",
    "ComputeNotFoundByName",
    "FailoverSegmentExists",
    "HostExists",
    "Unauthorized",
    "ObjectActionError",
    "OrphanedObjectError",
    "DuplicateNotification",
    "HostOnMaintenanceError",
    "HostRecoveryFailureException",
    "InstanceRecoveryFailureException",
    "SkipInstanceRecoveryException",
    "SkipProcessRecoveryException",
    "SkipHostRecoveryException",
    "ProcessRecoveryFailureException",
    "DBNotAllowed",
    "FailoverSegmentInUse",
    "HostInUse",
    "ReservedHostsUnavailable",
    "LockAlreadyAcquired",
    "IgnoreInstanceRecoveryException",
    "HostNotFoundUnderFailoverSegment",
    "InstanceEvacuateFailed",
    "FailoverSegmentDisabled",
]
