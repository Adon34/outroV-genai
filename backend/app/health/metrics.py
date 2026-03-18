from prometheus_client import Counter, Histogram, Gauge, Info
import time

# Health check metrics
health_check_duration = Histogram(
    'health_check_duration_seconds',
    'Time spent performing health checks',
    ['component']
)

health_check_status = Gauge(
    'health_check_status',
    'Health status of components (1=healthy, 0=unhealthy)',
    ['component']
)

health_check_response_time = Histogram(
    'health_check_response_time_ms',
    'Response time for health checks in milliseconds',
    ['component']
)

# Component-specific metrics
database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

database_connections_utilization = Gauge(
    'database_connections_utilization_percent',
    'Database connection pool utilization percentage'
)

redis_memory_used_mb = Gauge(
    'redis_memory_used_mb',
    'Redis memory usage in MB'
)

redis_memory_utilization = Gauge(
    'redis_memory_utilization_percent',
    'Redis memory utilization percentage'
)

redis_connected_clients = Gauge(
    'redis_connected_clients',
    'Number of connected Redis clients'
)

chroma_collections_count = Gauge(
    'chroma_collections_count',
    'Number of ChromaDB collections'
)

# Application info
app_info = Info('app_info', 'Application information')
app_info.info({
    'version': '1.0.0',
    'name': 'outroV_genai'
})

def update_health_metrics(component: str, health_status: str, response_time_ms: float = None, details: dict = None):
    """Update Prometheus metrics for a component"""
    # Status gauge
    status_value = 1 if health_status == "healthy" else 0
    health_check_status.labels(component=component).set(status_value)

    # Response time
    if response_time_ms is not None:
        health_check_response_time.labels(component=component).observe(response_time_ms)

    # Component-specific metrics
    if details:
        if component == "database":
            database_connections_active.set(details.get('active_connections', 0))
            database_connections_utilization.set(details.get('connection_utilization_percent', 0))
        elif component == "redis":
            redis_memory_used_mb.set(details.get('memory_used_mb', 0))
            redis_memory_utilization.set(details.get('memory_used_percent', 0))
            redis_connected_clients.set(details.get('connected_clients', 0))
        elif component == "chroma":
            chroma_collections_count.set(details.get('collections_count', 0))