# flake8: noqa
# pylint: disable=C0301

# From:
#  - https://github.com/openstack/octavia/blob/master/octavia/common/exceptions.py
#  - https://github.com/openstack/octavia/blob/master/octavia/amphorae/driver_exceptions/exceptions.py
# sed -rn 's/^class\s+(\S+)\(.+/    "\1",/p' octavia/common/exceptions.py
# sed -rn 's/^class\s+(\S+)\(.+/    "\1",/p' octavia/network/base.py
OCTAVIA_EXCEPTIONS = [
# common/exceptions.py
    "OctaviaException",
    "APIException",
    "NotFound",
    "PolicyForbidden",
    "InvalidOption",
    "InvalidFilterArgument",
    "DisabledOption",
    "L7RuleValidation",
    "SingleCreateDetailsMissing",
    "InvalidHMACException",
    "MissingArguments",
    "NetworkConfig",
    "NeedsPassphrase",
    "UnreadableCert",
    "UnreadablePKCS12",
    "MisMatchedKey",
    "CertificateRetrievalException",
    "CertificateStorageException",
    "CertificateGenerationException",
    "DuplicateListenerEntry",
    "DuplicateMemberEntry",
    "DuplicateHealthMonitor",
    "DuplicatePoolEntry",
    "PoolInUseByL7Policy",
    "ImmutableObject",
    "LBPendingStateError",
    "TooManyL7RulesOnL7Policy",
    "ComputeBuildException",
    "ComputeBuildQueueTimeoutException",
    "ComputeDeleteException",
    "ComputeGetException",
    "ComputeStatusException",
    "ComputeGetInterfaceException",
    "IDAlreadyExists",
    "RecordAlreadyExists",
    "NoReadyAmphoraeException",
    "ImageGetException",
    "ComputeWaitTimeoutException",
    "ComputePortInUseException",
    "ComputeUnknownException",
    "InvalidTopology",
    "InvalidL7PolicyAction",
    "InvalidL7PolicyArgs",
    "InvalidURL",
    "InvalidURLPath",
    "InvalidString",
    "InvalidRegex",
    "InvalidL7Rule",
    "ServerGroupObjectCreateException",
    "ServerGroupObjectDeleteException",
    "InvalidAmphoraOperatingSystem",
    "QuotaException",
    "ProjectBusyException",
    "MissingProjectID",
    "MissingAPIProjectID",
    "InvalidSubresource",
    "ValidationException",
    "VIPValidationException",
    "InvalidSortKey",
    "InvalidSortDirection",
    "InvalidMarker",
    "InvalidLimit",
    "MissingVIPSecurityGroup",
    "ProviderNotEnabled",
    "ProviderNotFound",
    "ProviderDriverError",
    "ProviderNotImplementedError",
    "ProviderUnsupportedOptionError",
    "InputFileError",
    "ObjectInUse",
    "ProviderFlavorMismatchError",
    "VolumeDeleteException",
    "VolumeGetException",
    "NetworkServiceError",
    "InvalidIPAddress",
# amphora/driver_exceptions/exceptions.py
    "AmphoraDriverError",
    "NotFoundError",
    "InfoException",
    "MetricsException",
    "UnauthorizedException",
    "StatisticsException",
    "TimeOutException",
    "DeleteFailed",
    "SuspendFailed",
    "EnableFailed",
    "ArchiveException",
    "ProvisioningErrors",
    "ListenerProvisioningError",
    "LoadBalancerProvisoningError",
    "HealthMonitorProvisioningError",
    "NodeProvisioningError",
    "AmpDriverNotImplementedError",
    "AmpConnectionRetry",
# network/base.py
    "NetworkException",
    "PlugVIPException",
    "UnplugVIPException",
    "AllocateVIPException",
    "DeallocateVIPException",
    "PlugNetworkException",
    "UnplugNetworkException",
    "VIPInUseException",
    "PortNotFound",
    "NetworkNotFound",
    "SubnetNotFound",
    "AmphoraNotFound",
    "PluggedVIPNotFound",
    "TimeoutException",
    "QosPolicyNotFound",
    "SecurityGroupNotFound",
    "CreatePortException",
    "AbstractNetworkDriver",
]