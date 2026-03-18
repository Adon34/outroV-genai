from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass
class ComponentHealth:
    """Health status for a single component"""
    status: str  # "healthy", "degraded", "unhealthy"
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    last_checked: Optional[datetime] = None

@dataclass
class HealthMatrix:
    """Overall health matrix response"""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    components: Dict[str, ComponentHealth]
    dependencies: list[str]
    version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "components": {
                name: {
                    "status": comp.status,
                    "response_time_ms": comp.response_time_ms,
                    "details": comp.details,
                    "error_message": comp.error_message,
                    "last_checked": comp.last_checked.isoformat() if comp.last_checked else None
                }
                for name, comp in self.components.items()
            },
            "dependencies": self.dependencies,
            "version": self.version
        }