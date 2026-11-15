from enum import Enum
class Role(str, Enum):
    platform_admin = 'platform_admin'
    admin = 'admin'
    analyst = 'analyst'
    viewer = 'viewer'
class JobStatus(str, Enum):
    queued = 'queued'
    running = 'running'
    completed = 'completed'
    failed = 'failed'
class ClaimStatus(str, Enum):
    pending = 'pending'
    claimed = 'claimed'
    conflict = 'conflict'
