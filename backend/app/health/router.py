from fastapi import APIRouter, HTTPException
from datetime import datetime
import asyncio

from .checks import perform_health_checks
from .models import HealthMatrix
from .metrics import update_health_metrics, health_check_duration

router = APIRouter()

@router.get("/health")
async def health_matrix():
    """
    Comprehensive health matrix by component.
    Returns detailed health status for all system components.
    """
    start_time = time.time()
    try:
        # Perform all health checks concurrently
        component_healths = await perform_health_checks()

        # Update Prometheus metrics
        for component, health in component_healths.items():
            update_health_metrics(
                component=component,
                health_status=health.status,
                response_time_ms=health.response_time_ms,
                details=health.details
            )

        # Determine overall status
        statuses = [h.status for h in component_healths.values()]
        if all(s == "healthy" for s in statuses):
            overall_status = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        # Create health matrix response
        health_matrix = HealthMatrix(
            status=overall_status,
            timestamp=datetime.now(),
            components=component_healths,
            dependencies=["database", "redis", "chroma", "openai"],
            version="1.0.0"
        )

        # Record total check duration
        duration = time.time() - start_time
        health_check_duration.labels(component="overall").observe(duration)

        return health_matrix.to_dict()

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@router.get("/health/live")
async def liveness_probe():
    """
    Liveness probe - checks if the application is running.
    Used by Kubernetes/Docker for container health.
    """
    return {"status": "alive", "timestamp": datetime.now().isoformat()}

@router.get("/health/ready")
async def readiness_probe():
    """
    Readiness probe - checks if the application is ready to serve traffic.
    Performs quick checks on critical dependencies.
    """
    try:
        # Quick checks for critical components
        from .checks import check_database, check_redis

        db_health = await check_database()
        redis_health = await check_redis()

        if db_health.status == "healthy" and redis_health.status == "healthy":
            return {"status": "ready", "timestamp": datetime.now().isoformat()}
        else:
            raise HTTPException(status_code=503, detail="Critical dependencies not ready")

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Readiness check failed: {str(e)}")

@router.get("/health/{component}")
async def component_health(component: str):
    """
    Get health status for a specific component.
    """
    component_checks = {
        "database": "check_database",
        "redis": "check_redis",
        "chroma": "check_chroma",
        "rag_service": "check_rag_service",
        "openai": "check_openai"
    }

    if component not in component_checks:
        raise HTTPException(status_code=404, detail=f"Component '{component}' not found")

    try:
        from . import checks
        check_func = getattr(checks, component_checks[component])
        health = await check_func()

        # Update metrics
        update_health_metrics(
            component=component,
            health_status=health.status,
            response_time_ms=health.response_time_ms,
            details=health.details
        )

        return {
            "component": component,
            "health": health.__dict__
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Component health check failed: {str(e)}")