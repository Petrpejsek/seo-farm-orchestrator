"""
🔍 PROMETHEUS METRIKY PRO SEO FARM
Sbírání a export metrik pro monitoring.
"""

import time
import logging
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry
import psutil
import os

# Metriky
REGISTRY = CollectorRegistry()

# Workflow metriky
workflow_total = Counter(
    'seo_farm_workflows_total',
    'Celkový počet workflow',
    ['status', 'workflow_type'],
    registry=REGISTRY
)

workflow_duration = Histogram(
    'seo_farm_workflow_duration_seconds',
    'Doba trvání workflow',
    ['workflow_type'],
    registry=REGISTRY
)

# LLM metriky
llm_requests_total = Counter(
    'seo_farm_llm_requests_total',
    'Celkový počet LLM requestů',
    ['provider', 'model', 'status'],
    registry=REGISTRY
)

llm_response_time = Histogram(
    'seo_farm_llm_response_time_seconds',
    'Doba odezvy LLM',
    ['provider', 'model'],
    registry=REGISTRY
)

llm_tokens_total = Counter(
    'seo_farm_llm_tokens_total',
    'Celkový počet tokenů',
    ['provider', 'model', 'type'],  # type: prompt|completion
    registry=REGISTRY
)

# Worker metriky
worker_activities_total = Counter(
    'seo_farm_worker_activities_total',
    'Celkový počet aktivit',
    ['activity_name', 'status'],
    registry=REGISTRY
)

worker_heartbeats_total = Counter(
    'seo_farm_worker_heartbeats_total',
    'Celkový počet heartbeats',
    registry=REGISTRY
)

# Systémové metriky
system_cpu_usage = Gauge(
    'seo_farm_system_cpu_usage_percent',
    'CPU využití',
    registry=REGISTRY
)

system_memory_usage = Gauge(
    'seo_farm_system_memory_usage_percent',
    'Paměť využití',
    registry=REGISTRY
)

system_disk_usage = Gauge(
    'seo_farm_system_disk_usage_percent',
    'Disk využití',
    registry=REGISTRY
)

# Queue metriky
queue_depth = Gauge(
    'seo_farm_queue_depth',
    'Hloubka fronty',
    ['queue_name'],
    registry=REGISTRY
)

class MetricsCollector:
    """Sběrač metrik pro SEO Farm."""
    
    def __init__(self, port: int = 9090):
        self.port = port
        self.logger = logging.getLogger(__name__)
    
    def start_server(self):
        """Spustí Prometheus metrics server."""
        try:
            start_http_server(self.port, registry=REGISTRY)
            self.logger.info(f"📊 Prometheus metrics server spuštěn na portu {self.port}")
        except Exception as e:
            self.logger.error(f"❌ Chyba při spuštění metrics serveru: {e}")
    
    def update_system_metrics(self):
        """Aktualizuje systémové metriky."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            system_cpu_usage.set(cpu_percent)
            
            # Memory
            memory = psutil.virtual_memory()
            system_memory_usage.set(memory.percent)
            
            # Disk
            disk = psutil.disk_usage('.')
            disk_percent = (disk.used / disk.total) * 100
            system_disk_usage.set(disk_percent)
            
        except Exception as e:
            self.logger.error(f"❌ Chyba při aktualizaci systémových metrik: {e}")
    
    def record_workflow_start(self, workflow_type: str):
        """Zaznamenání začátku workflow."""
        workflow_total.labels(status='started', workflow_type=workflow_type).inc()
    
    def record_workflow_success(self, workflow_type: str, duration: float):
        """Zaznamenání úspěšného workflow."""
        workflow_total.labels(status='success', workflow_type=workflow_type).inc()
        workflow_duration.labels(workflow_type=workflow_type).observe(duration)
    
    def record_workflow_error(self, workflow_type: str, duration: float):
        """Zaznamenání chybného workflow."""
        workflow_total.labels(status='error', workflow_type=workflow_type).inc()
        workflow_duration.labels(workflow_type=workflow_type).observe(duration)
    
    def record_llm_request(self, provider: str, model: str, 
                          response_time: float, prompt_tokens: int = 0, 
                          completion_tokens: int = 0, success: bool = True):
        """Zaznamenání LLM requestu."""
        status = 'success' if success else 'error'
        
        llm_requests_total.labels(
            provider=provider, 
            model=model, 
            status=status
        ).inc()
        
        if success:
            llm_response_time.labels(
                provider=provider, 
                model=model
            ).observe(response_time)
            
            if prompt_tokens > 0:
                llm_tokens_total.labels(
                    provider=provider, 
                    model=model, 
                    type='prompt'
                ).inc(prompt_tokens)
            
            if completion_tokens > 0:
                llm_tokens_total.labels(
                    provider=provider, 
                    model=model, 
                    type='completion'
                ).inc(completion_tokens)
    
    def record_activity(self, activity_name: str, success: bool = True):
        """Zaznamenání aktivity."""
        status = 'success' if success else 'error'
        worker_activities_total.labels(
            activity_name=activity_name, 
            status=status
        ).inc()
    
    def record_heartbeat(self):
        """Zaznamenání heartbeat."""
        worker_heartbeats_total.inc()
    
    def set_queue_depth(self, queue_name: str, depth: int):
        """Nastavení hloubky fronty."""
        queue_depth.labels(queue_name=queue_name).set(depth)

# Globální instance
metrics = MetricsCollector()

def get_metrics_collector() -> MetricsCollector:
    """Vrátí globální metrics collector."""
    return metrics