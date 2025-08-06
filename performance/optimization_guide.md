# ⚡ PERFORMANCE OPTIMIZATION GUIDE

## 📊 SOUČASNÝ VÝKON

### Baseline měření (3.8.2025):
- **Worker throughput**: ~1 workflow/15 minut
- **LLM response time**: 10-20s (OpenAI GPT-4o)
- **Memory usage**: ~100MB worker proces
- **CPU usage**: 5-15% idle, 80%+ during LLM calls

## 🎯 OPTIMALIZAČNÍ CÍLE

### Krátkodobé (týden):
- ⬆️ **Worker throughput**: 3-4 workflows parallelně  
- ⬇️ **LLM response time**: <10s průměr
- ⬇️ **Memory usage**: <80MB per worker
- ⚡ **Pipeline latency**: <5 minut celkem

### Dlouhodobé (měsíc):
- 🚀 **Auto-scaling**: 1-10 workers based on queue
- 📈 **Throughput**: 50+ workflows/hodina
- 💾 **Caching**: 90%+ cache hit rate pro opakované dotazy
- 🌐 **CDN**: <2s frontend load time

## 🛠️ OPTIMALIZACE IMPLEMENTACE

### 1. Worker Pool Scaling
```python
# config.py - Enhanced worker configuration
WORKER_CONFIG = {
    "min_workers": 2,
    "max_workers": 8,
    "scale_up_threshold": 5,    # items in queue
    "scale_down_threshold": 1,
    "worker_memory_limit": "512MB",
    "worker_cpu_limit": "1.0"
}
```

### 2. LLM Request Optimization
```python
# Batch processing
async def process_batch_llm_requests(requests: List[LLMRequest]):
    tasks = [process_single_request(req) for req in requests]
    return await asyncio.gather(*tasks, return_exceptions=True)

# Connection pooling
class LLMClientPool:
    def __init__(self, pool_size: int = 5):
        self.pool = asyncio.Queue(maxsize=pool_size)
        # Initialize connection pool
```

### 3. Caching Strategy
```python
# Redis cache pro LLM responses
CACHE_CONFIG = {
    "redis_url": "redis://localhost:6379/0",
    "ttl_seconds": 3600,  # 1 hour
    "cache_keys": [
        "llm_response_{provider}_{model}_{hash}",
        "assistant_output_{assistant_id}_{input_hash}"
    ]
}
```

## 📈 MONITORING METRIKY

### Worker Performance
```prometheus
# Throughput
rate(seo_farm_workflows_total[5m])

# Queue depth
seo_farm_queue_depth

# Worker utilization  
seo_farm_workers_active / seo_farm_workers_total * 100
```

### LLM Performance
```prometheus
# Response time percentiles
histogram_quantile(0.95, seo_farm_llm_response_time_seconds_bucket)

# Error rate
rate(seo_farm_llm_requests_total{status="error"}[5m]) / 
rate(seo_farm_llm_requests_total[5m]) * 100

# Token efficiency
seo_farm_llm_tokens_total{type="completion"} / 
seo_farm_llm_tokens_total{type="prompt"}
```

## 🚀 IMPLEMENTATION ROADMAP

### Phase 1: Parallel Processing (Week 1)
- [ ] Multiple worker instances
- [ ] Async LLM client pool
- [ ] Queue-based task distribution
- [ ] Basic load balancing

### Phase 2: Caching Layer (Week 2)  
- [ ] Redis integration
- [ ] LLM response caching
- [ ] Smart cache invalidation
- [ ] Cache metrics

### Phase 3: Auto-scaling (Week 3)
- [ ] Queue depth monitoring
- [ ] Dynamic worker spawning
- [ ] Resource limits
- [ ] Graceful shutdown

### Phase 4: Advanced Optimizations (Week 4)
- [ ] LLM model selection based on complexity
- [ ] Prompt optimization
- [ ] Response streaming
- [ ] CDN for static assets

## 💾 MEMORY OPTIMIZATION

### Current Issues:
- LLM clients hold persistent connections
- Large response objects not GC'd promptly
- Temporal workflow state accumulation

### Solutions:
```python
# Explicit memory management
import gc
import psutil

class MemoryMonitor:
    def __init__(self, threshold_mb: int = 100):
        self.threshold = threshold_mb * 1024 * 1024
    
    def check_and_cleanup(self):
        process = psutil.Process()
        if process.memory_info().rss > self.threshold:
            gc.collect()
            # Force cleanup of LLM clients
            await self.cleanup_llm_connections()
```

## 🌐 NETWORK OPTIMIZATION

### Connection Pooling:
```python
# HTTP connection reuse
import aiohttp

session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(
        limit=100,
        limit_per_host=10,
        keepalive_timeout=30
    )
)
```

### Request Optimization:
- Compress requests/responses
- Use HTTP/2 where possible
- Implement request timeouts
- Retry with exponential backoff

## 📊 LOAD TESTING

### Test Scenarios:
```bash
# Concurrent workflows
python scripts/load_test.py --workflows 10 --concurrent 3

# Stress testing
python scripts/stress_test.py --duration 300 --ramp-up 60

# Memory leak detection
python scripts/memory_test.py --workflows 100 --monitor-memory
```

### Performance Targets:
- **P95 response time**: <15 seconds
- **Error rate**: <1%
- **Memory growth**: <10MB/hour
- **CPU efficiency**: >80% during load

## 🎛️ TUNING PARAMETERS

### LLM Settings:
```python
# Model selection based on task complexity
MODEL_ROUTING = {
    "simple": "gpt-3.5-turbo",      # Fast, cheap
    "complex": "gpt-4o",            # Slow, accurate  
    "creative": "claude-3-sonnet"   # Balanced
}

# Dynamic timeout based on model
TIMEOUTS = {
    "gpt-3.5-turbo": 30,
    "gpt-4o": 60,
    "claude-3-sonnet": 45
}
```

### Temporal Configuration:
```python
# Optimized activity settings
ACTIVITY_OPTIONS = {
    "start_to_close_timeout": timedelta(minutes=5),  # Reduced
    "heartbeat_timeout": timedelta(minutes=1),       # More frequent
    "maximum_attempts": 2,                          # Faster failure
}
```