# Design Document: Production Readiness

## Executive Summary

This document outlines the technical design for transforming the Document QA RAG Agent from a functional prototype into a production-ready enterprise system. The design addresses 30 requirements across security, reliability, scalability, observability, and operational excellence.

The system currently consists of a FastAPI backend and Streamlit UI with pluggable vector stores (FAISS/Qdrant) and LLM providers (Gemini/OpenAI). The production readiness initiative will add enterprise-grade capabilities while maintaining the existing architecture's flexibility and simplicity.

## Design Principles

1. **Backward Compatibility**: Existing functionality remains unchanged; production features are additive
2. **Configuration-Driven**: All production features can be enabled/disabled via configuration
3. **Cloud-Native**: Design for containerized deployment on Kubernetes with horizontal scaling
4. **Defense in Depth**: Multiple layers of security controls
5. **Observable by Default**: Comprehensive logging, metrics, and tracing built-in
6. **Fail Gracefully**: Circuit breakers, retries, and degradation strategies throughout

## Architecture Overview

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Load Balancer / Ingress                      │
│                    (TLS Termination, Rate Limiting)                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
         ┌──────────▼──────────┐   ┌─────────▼──────────┐
         │   API Service       │   │   UI Service        │
         │   (FastAPI)         │   │   (Streamlit)       │
         │   - Auth Middleware │   │   - Session Mgmt    │
         │   - Rate Limiting   │   │   - API Client      │
         │   - Metrics         │   │                     │
         └──────────┬──────────┘   └─────────────────────┘
                    │
      ┌─────────────┼─────────────┬──────────────┐
      │             │             │              │
┌─────▼─────┐ ┌────▼────┐  ┌─────▼─────┐  ┌────▼────┐
│  Vector   │ │   LLM   │  │ Embedding │  │  Redis  │
│  Store    │ │ Provider│  │  Service  │  │  Cache  │
│ (Qdrant)  │ │(Gemini) │  │           │  │         │
└───────────┘ └─────────┘  └───────────┘  └─────────┘
      │
┌─────▼─────┐
│ Document  │
│  Storage  │
│   (S3)    │
└───────────┘

         Observability Stack
┌──────────────────────────────────────┐
│  Prometheus  │  Jaeger  │  ELK/Loki │
│  (Metrics)   │ (Traces) │   (Logs)  │
└──────────────────────────────────────┘
```

## Component Designs


### 1. Authentication and Authorization System

#### Design Overview

Implement JWT-based authentication with role-based access control (RBAC) using FastAPI's dependency injection system.

#### Components

**1.1 Authentication Service** (`src/auth/auth_service.py`)
- User credential storage with bcrypt hashing (cost factor: 12)
- JWT token generation and validation (HS256 algorithm)
- Token refresh mechanism
- Session management with Redis backend

**1.2 Authorization Middleware** (`src/auth/middleware.py`)
- Role-based access control decorator
- Permission checking per endpoint
- Audit logging for auth events

**1.3 User Management** (`src/auth/user_manager.py`)
- User CRUD operations
- Password policy enforcement (12+ chars, complexity requirements)
- Account lockout after failed attempts (5 attempts, 15-minute lockout)

#### Data Model

```python
class User:
    id: UUID
    username: str
    email: str
    password_hash: str
    role: UserRole  # ADMIN, USER
    created_at: datetime
    last_login: datetime
    is_active: bool
    failed_login_attempts: int
    locked_until: Optional[datetime]

class Session:
    session_id: UUID
    user_id: UUID
    access_token: str
    refresh_token: str
    expires_at: datetime
    created_at: datetime
```

#### API Endpoints

```
POST   /auth/register          - Create new user account
POST   /auth/login             - Authenticate and get tokens
POST   /auth/refresh           - Refresh access token
POST   /auth/logout            - Invalidate session
GET    /auth/me                - Get current user info
PUT    /auth/password          - Change password
```

#### Configuration

```python
# .env additions
JWT_SECRET_KEY=<random-256-bit-key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
PASSWORD_MIN_LENGTH=12
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15
```

#### Implementation Notes

- Use `python-jose` for JWT handling
- Use `passlib` with bcrypt for password hashing
- Store sessions in Redis for distributed deployment
- Implement token blacklist for logout
- Add rate limiting on auth endpoints (10 requests/minute per IP)



### 2. API Security Layer

#### Design Overview

Implement comprehensive input validation, rate limiting, and security headers using FastAPI middleware and dependencies.

#### Components

**2.1 Input Validation** (`src/security/validation.py`)
- Pydantic models with strict validation
- File upload validation (type, size, content)
- SQL injection prevention (parameterized queries)
- XSS prevention (input sanitization)

**2.2 Rate Limiting** (`src/security/rate_limiter.py`)
- Token bucket algorithm with Redis backend
- Per-endpoint rate limits
- Per-user and per-IP tracking
- Configurable limits and windows

**2.3 Security Middleware** (`src/security/middleware.py`)
- Security headers injection
- CORS policy enforcement
- Request size limits
- Content-Type validation

#### Rate Limit Configuration

```python
RATE_LIMITS = {
    "/auth/login": "10/minute",
    "/auth/register": "5/hour",
    "/upload": "20/hour",
    "/query": "100/hour",
    "default": "1000/hour"
}
```

#### Security Headers

```python
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}
```

#### File Upload Validation

```python
class FileValidator:
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_MIME_TYPES = ["application/pdf"]
    
    def validate_file(self, file: UploadFile):
        # Check file extension
        # Verify MIME type
        # Scan file content (magic bytes)
        # Check file size
        # Scan for malware (optional: ClamAV integration)
```

#### Configuration

```python
# .env additions
ENABLE_RATE_LIMITING=true
RATE_LIMIT_STORAGE=redis://localhost:6379/1
MAX_REQUEST_SIZE_MB=100
CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
ENABLE_SECURITY_HEADERS=true
```



### 3. Secrets Management

#### Design Overview

Integrate with cloud-native secrets management services while supporting local development with environment variables.

#### Architecture

```
Application Startup
    │
    ├─> Check SECRETS_BACKEND env var
    │
    ├─> If "aws": Load from AWS Secrets Manager
    ├─> If "gcp": Load from GCP Secret Manager
    ├─> If "vault": Load from HashiCorp Vault
    └─> If "env": Load from environment variables (dev only)
```

#### Components

**3.1 Secrets Provider Interface** (`src/secrets/provider.py`)

```python
class SecretsProvider(ABC):
    @abstractmethod
    async def get_secret(self, key: str) -> str:
        pass
    
    @abstractmethod
    async def list_secrets(self) -> List[str]:
        pass
    
    @abstractmethod
    async def rotate_secret(self, key: str, new_value: str):
        pass
```

**3.2 Provider Implementations**
- `AWSSecretsProvider`: AWS Secrets Manager integration
- `GCPSecretsProvider`: GCP Secret Manager integration
- `VaultSecretsProvider`: HashiCorp Vault integration
- `EnvSecretsProvider`: Environment variables (dev/test only)

**3.3 Secrets Manager** (`src/secrets/manager.py`)

```python
class SecretsManager:
    def __init__(self, provider: SecretsProvider):
        self.provider = provider
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def get_secret(self, key: str, required: bool = True) -> Optional[str]:
        # Check cache
        # Fetch from provider
        # Validate and return
        # Mask in logs
```

#### Secret Rotation Strategy

```python
# Automated rotation schedule
ROTATION_SCHEDULE = {
    "api_keys": 90,      # days
    "database_passwords": 30,
    "jwt_secret": 180
}
```

#### Configuration

```python
# .env additions
SECRETS_BACKEND=gcp  # aws, gcp, vault, env
AWS_SECRETS_REGION=us-east-1
GCP_PROJECT_ID=my-project
VAULT_ADDR=https://vault.example.com
VAULT_TOKEN=<token>
SECRETS_CACHE_TTL=300
```

#### Required Secrets

```
- GEMINI_API_KEY
- OPENAI_API_KEY
- QDRANT_API_KEY
- JWT_SECRET_KEY
- DATABASE_PASSWORD
- REDIS_PASSWORD
- ENCRYPTION_KEY (for data at rest)
```

#### Implementation Notes

- Secrets are never logged in plain text
- Implement secret redaction in log formatter
- Validate all required secrets at startup
- Fail fast if critical secrets are missing
- Support secret versioning for rollback



### 4. Observability Stack

#### Design Overview

Implement the three pillars of observability: logging, metrics, and distributed tracing using industry-standard tools and formats.

#### 4.1 Structured Logging

**Components** (`src/observability/logging.py`)

```python
class StructuredLogger:
    def __init__(self):
        self.logger = structlog.get_logger()
        self.correlation_id_var = contextvars.ContextVar('correlation_id')
    
    def log(self, level, message, **kwargs):
        # Add correlation ID
        # Add timestamp
        # Add service metadata
        # Redact sensitive fields
        # Output as JSON
```

**Log Format**

```json
{
  "timestamp": "2026-03-02T10:15:30.123Z",
  "level": "INFO",
  "service": "docqa-api",
  "version": "1.0.0",
  "correlation_id": "abc-123-def",
  "user_id": "user-456",
  "endpoint": "/query",
  "method": "POST",
  "status_code": 200,
  "duration_ms": 245,
  "message": "Query processed successfully",
  "context": {
    "question_length": 50,
    "top_k": 5,
    "confidence_score": 0.85
  }
}
```

**Sensitive Data Redaction**

```python
REDACT_PATTERNS = [
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    r'\b(?:\d{4}[-\s]?){3}\d{4}\b',  # Credit card
    r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]+',  # API keys
]
```

#### 4.2 Metrics Collection

**Components** (`src/observability/metrics.py`)

```python
from prometheus_client import Counter, Histogram, Gauge, Info

# Request metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Business metrics
documents_indexed = Gauge(
    'documents_indexed_total',
    'Total documents in vector store'
)

queries_processed = Counter(
    'queries_processed_total',
    'Total queries processed',
    ['status']
)

# LLM metrics
llm_tokens_used = Counter(
    'llm_tokens_used_total',
    'Total LLM tokens consumed',
    ['provider', 'model']
)

llm_request_duration = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration',
    ['provider', 'model']
)

# Vector store metrics
vector_search_duration = Histogram(
    'vector_search_duration_seconds',
    'Vector search duration'
)

# System metrics
cpu_usage = Gauge('cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('memory_usage_bytes', 'Memory usage in bytes')
```

**Metrics Endpoint**

```python
@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

#### 4.3 Distributed Tracing

**Components** (`src/observability/tracing.py`)

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

class TracingManager:
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)
    
    def trace_request(self, name: str):
        # Create span
        # Add attributes
        # Propagate context
        # Export to backend
```

**Trace Spans**

```
Query Request (root span)
├── Authenticate User
├── Validate Input
├── Generate Query Embedding
│   └── Call Embedding API
├── Vector Search
│   ├── Connect to Qdrant
│   └── Execute Search
├── Generate Answer
│   ├── Build Prompt
│   └── Call LLM API
└── Format Response
```

**Span Attributes**

```python
span.set_attribute("user.id", user_id)
span.set_attribute("query.length", len(question))
span.set_attribute("query.top_k", top_k)
span.set_attribute("vector_store.backend", "qdrant")
span.set_attribute("llm.provider", "gemini")
span.set_attribute("llm.model", "gemini-1.5-flash")
span.set_attribute("llm.tokens", token_count)
```

#### Configuration

```python
# .env additions
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_METRICS=true
METRICS_PORT=9090
ENABLE_TRACING=true
TRACING_BACKEND=jaeger  # jaeger, zipkin, xray
JAEGER_ENDPOINT=http://jaeger:14268/api/traces
TRACING_SAMPLE_RATE=0.1  # 10% sampling
```



### 5. Health Checks and Readiness Probes

#### Design Overview

Implement comprehensive health checks that validate all system dependencies for Kubernetes liveness and readiness probes.

#### Components

**5.1 Health Check Service** (`src/health/health_service.py`)

```python
class HealthChecker:
    def __init__(self):
        self.checks = {
            "vector_store": self.check_vector_store,
            "llm_provider": self.check_llm_provider,
            "embedding_service": self.check_embedding_service,
            "redis": self.check_redis,
            "document_storage": self.check_document_storage
        }
    
    async def check_liveness(self) -> HealthStatus:
        # Basic application health
        # Returns 200 if app is running
        return HealthStatus(status="healthy")
    
    async def check_readiness(self) -> HealthStatus:
        # Check all dependencies
        # Returns 503 if any dependency is down
        results = await self.run_all_checks()
        return self.aggregate_results(results)
    
    async def check_vector_store(self) -> ComponentHealth:
        try:
            # Ping Qdrant
            # Check collection exists
            # Verify read/write access
            return ComponentHealth(
                name="vector_store",
                status="healthy",
                latency_ms=12
            )
        except Exception as e:
            return ComponentHealth(
                name="vector_store",
                status="unhealthy",
                error=str(e)
            )
```

#### API Endpoints

```python
@app.get("/health/live")
async def liveness():
    """Kubernetes liveness probe - is the app running?"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe - can the app serve traffic?"""
    health = await health_checker.check_readiness()
    status_code = 200 if health.is_ready else 503
    return JSONResponse(
        status_code=status_code,
        content=health.dict()
    )

@app.get("/health/startup")
async def startup():
    """Kubernetes startup probe - has the app finished initializing?"""
    # Check if all services are initialized
    # Used for slow-starting applications
    return {"status": "ready", "initialized": True}
```

#### Response Format

```json
{
  "status": "healthy",
  "timestamp": "2026-03-02T10:15:30Z",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "components": {
    "vector_store": {
      "status": "healthy",
      "backend": "qdrant",
      "latency_ms": 12,
      "documents_count": 150
    },
    "llm_provider": {
      "status": "healthy",
      "provider": "gemini",
      "model": "gemini-1.5-flash",
      "latency_ms": 45
    },
    "embedding_service": {
      "status": "healthy",
      "provider": "sentence-transformers",
      "model": "all-MiniLM-L6-v2",
      "latency_ms": 8
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 3
    },
    "document_storage": {
      "status": "healthy",
      "backend": "s3",
      "latency_ms": 25
    }
  }
}
```

#### Kubernetes Configuration

```yaml
# deployment.yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 5
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /health/startup
    port: 8080
  initialDelaySeconds: 0
  periodSeconds: 5
  timeoutSeconds: 5
  failureThreshold: 30  # 150 seconds max startup time
```



### 6. Error Handling and Resilience

#### Design Overview

Implement circuit breakers, retries with exponential backoff, and graceful degradation for external service failures.

#### Components

**6.1 Circuit Breaker** (`src/resilience/circuit_breaker.py`)

```python
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError()
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

**6.2 Retry Strategy** (`src/resilience/retry.py`)

```python
class RetryStrategy:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    async def execute(self, func, *args, **kwargs):
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except RetryableException as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        return delay
```

**6.3 Timeout Manager** (`src/resilience/timeout.py`)

```python
class TimeoutManager:
    TIMEOUTS = {
        "llm_request": 30.0,
        "embedding_request": 10.0,
        "vector_search": 5.0,
        "document_upload": 120.0,
        "health_check": 5.0
    }
    
    @staticmethod
    async def with_timeout(operation: str, coro):
        timeout = TimeoutManager.TIMEOUTS.get(operation, 30.0)
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise OperationTimeoutError(
                f"{operation} exceeded timeout of {timeout}s"
            )
```

#### Service-Specific Resilience

**LLM Provider Resilience**

```python
class ResilientLLMProvider:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
        self.retry_strategy = RetryStrategy(
            max_attempts=3,
            base_delay=1.0
        )
    
    async def generate_answer(self, prompt: str) -> str:
        return await self.circuit_breaker.call(
            self.retry_strategy.execute,
            self._generate_with_timeout,
            prompt
        )
    
    async def _generate_with_timeout(self, prompt: str) -> str:
        return await TimeoutManager.with_timeout(
            "llm_request",
            self.provider.generate(prompt)
        )
```

**Vector Store Resilience**

```python
class ResilientVectorStore:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30
        )
    
    async def search(self, query_vector: List[float], top_k: int):
        try:
            return await self.circuit_breaker.call(
                TimeoutManager.with_timeout,
                "vector_search",
                self.vector_store.search(query_vector, top_k)
            )
        except CircuitBreakerOpenError:
            # Graceful degradation: return cached results or error
            logger.warning("Vector store circuit breaker open")
            raise ServiceUnavailableError(
                "Search service temporarily unavailable"
            )
```

#### Graceful Degradation Strategies

```python
class GracefulDegradation:
    @staticmethod
    async def handle_llm_failure(question: str, context: str):
        # Return context without LLM-generated answer
        return {
            "answer": "Service temporarily unavailable. Here are relevant excerpts:",
            "context": context,
            "degraded": True
        }
    
    @staticmethod
    async def handle_embedding_failure():
        # Fall back to keyword search
        logger.warning("Embedding service unavailable, using keyword search")
        return KeywordSearchFallback()
```

#### Configuration

```python
# .env additions
ENABLE_CIRCUIT_BREAKER=true
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
ENABLE_RETRY=true
MAX_RETRY_ATTEMPTS=3
RETRY_BASE_DELAY=1.0
ENABLE_GRACEFUL_DEGRADATION=true
```



### 7. Containerization and Orchestration

#### 7.1 Docker Images

**Multi-Stage Dockerfile**

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN pip install uv && \
    uv pip install --system --no-cache-dir -r pyproject.toml

# Stage 2: Runtime
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY src/ ./src/
COPY .env.example .env

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health/live')"

# Expose port
EXPOSE 8080

# Run application
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Streamlit UI Dockerfile**

```dockerfile
FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY requirements-ui.txt .
RUN pip install --no-cache-dir -r requirements-ui.txt

COPY streamlit_app.py .
COPY src/ui_utils.py ./src/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### 7.2 Kubernetes Manifests

**Namespace**

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: docqa
  labels:
    name: docqa
    environment: production
```

**ConfigMap**

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: docqa-config
  namespace: docqa
data:
  VECTOR_STORE_BACKEND: "qdrant"
  QDRANT_HOST: "qdrant-service"
  QDRANT_PORT: "6333"
  EMBEDDING_PROVIDER: "sentence-transformers"
  LLM_PROVIDER: "gemini"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  ENABLE_METRICS: "true"
  ENABLE_TRACING: "true"
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
```

**Secrets**

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: docqa-secrets
  namespace: docqa
type: Opaque
stringData:
  GEMINI_API_KEY: ""  # Populated by CI/CD or external secrets operator
  QDRANT_API_KEY: ""
  JWT_SECRET_KEY: ""
  REDIS_PASSWORD: ""
```

**API Deployment**

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docqa-api
  namespace: docqa
  labels:
    app: docqa-api
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: docqa-api
  template:
    metadata:
      labels:
        app: docqa-api
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: docqa-api
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: api
        image: gcr.io/PROJECT_ID/docqa-api:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        - containerPort: 9090
          name: metrics
          protocol: TCP
        envFrom:
        - configMapRef:
            name: docqa-config
        - secretRef:
            name: docqa-secrets
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 5
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /health/startup
            port: 8080
          initialDelaySeconds: 0
          periodSeconds: 5
          timeoutSeconds: 5
          failureThreshold: 30
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: docqa-data-pvc
```

**Service**

```yaml
# k8s/api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: docqa-api-service
  namespace: docqa
  labels:
    app: docqa-api
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
    name: http
  - port: 9090
    targetPort: 9090
    protocol: TCP
    name: metrics
  selector:
    app: docqa-api
```

**Horizontal Pod Autoscaler**

```yaml
# k8s/api-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: docqa-api-hpa
  namespace: docqa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: docqa-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 2
        periodSeconds: 30
      selectPolicy: Max
```

**Ingress**

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: docqa-ingress
  namespace: docqa
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.docqa.example.com
    - app.docqa.example.com
    secretName: docqa-tls
  rules:
  - host: api.docqa.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: docqa-api-service
            port:
              number: 80
  - host: app.docqa.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: docqa-ui-service
            port:
              number: 80
```

**PersistentVolumeClaim**

```yaml
# k8s/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: docqa-data-pvc
  namespace: docqa
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: standard-rwo
  resources:
    requests:
      storage: 100Gi
```



### 8. CI/CD Pipeline

#### Design Overview

Implement automated build, test, security scanning, and deployment pipeline using GitHub Actions with multi-environment support.

#### Pipeline Architecture

```
Code Push → GitHub Actions
    │
    ├─> Lint & Format Check
    ├─> Unit Tests
    ├─> Integration Tests
    ├─> Security Scanning
    │   ├─> Dependency Vulnerability Scan (Snyk/Trivy)
    │   ├─> SAST (Bandit, Semgrep)
    │   └─> Container Image Scan
    ├─> Build Docker Images
    ├─> Push to Container Registry
    │
    ├─> Deploy to Staging (auto)
    ├─> Run E2E Tests
    │
    └─> Deploy to Production (manual approval)
```

#### GitHub Actions Workflow

```yaml
# .github/workflows/ci-cd.yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: gcr.io
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  IMAGE_NAME: docqa-api

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install --system -e ".[dev]"
      
      - name: Lint with ruff
        run: ruff check src/ tests/
      
      - name: Format check with black
        run: black --check src/ tests/
      
      - name: Type check with mypy
        run: mypy src/
      
      - name: Run unit tests
        run: pytest tests/ -v --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Bandit (SAST)
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-report.json
      
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: auto
      
      - name: Dependency vulnerability scan
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          command: test
          args: --severity-threshold=high

  build-and-push:
    needs: [lint-and-test, security-scan]
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Configure Docker for GCR
        run: gcloud auth configure-docker
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Scan image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  deploy-staging:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment:
      name: staging
      url: https://staging.docqa.example.com
    steps:
      - uses: actions/checkout@v4
      
      - name: Authenticate to GKE
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Get GKE credentials
        uses: google-github-actions/get-gke-credentials@v2
        with:
          cluster_name: docqa-staging
          location: us-central1
      
      - name: Deploy to staging
        run: |
          kubectl set image deployment/docqa-api \
            api=${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            -n docqa-staging
          kubectl rollout status deployment/docqa-api -n docqa-staging
      
      - name: Run smoke tests
        run: |
          python tests/e2e/smoke_tests.py --env staging

  deploy-production:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://api.docqa.example.com
    steps:
      - uses: actions/checkout@v4
      
      - name: Authenticate to GKE
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Get GKE credentials
        uses: google-github-actions/get-gke-credentials@v2
        with:
          cluster_name: docqa-production
          location: us-central1
      
      - name: Deploy to production
        run: |
          kubectl set image deployment/docqa-api \
            api=${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            -n docqa
          kubectl rollout status deployment/docqa-api -n docqa
      
      - name: Verify deployment
        run: |
          python tests/e2e/smoke_tests.py --env production
      
      - name: Rollback on failure
        if: failure()
        run: |
          kubectl rollout undo deployment/docqa-api -n docqa
          kubectl rollout status deployment/docqa-api -n docqa
```

#### Deployment Scripts

**Rollback Script** (`scripts/rollback.sh`)

```bash
#!/bin/bash
set -e

NAMESPACE=${1:-docqa}
DEPLOYMENT=${2:-docqa-api}

echo "Rolling back $DEPLOYMENT in namespace $NAMESPACE..."

kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE
kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE

echo "Rollback completed successfully"
```

**Health Check Script** (`scripts/health_check.sh`)

```bash
#!/bin/bash
set -e

API_URL=${1:-https://api.docqa.example.com}
MAX_RETRIES=30
RETRY_INTERVAL=10

for i in $(seq 1 $MAX_RETRIES); do
  echo "Health check attempt $i/$MAX_RETRIES..."
  
  if curl -sf "$API_URL/health/ready" > /dev/null; then
    echo "Service is healthy"
    exit 0
  fi
  
  sleep $RETRY_INTERVAL
done

echo "Service failed to become healthy"
exit 1
```



### 9. Performance Optimization and Caching

#### Design Overview

Implement multi-layer caching strategy to reduce latency and external API costs.

#### Caching Architecture

```
Request → API Gateway
    │
    ├─> L1: In-Memory Cache (LRU, 1000 items)
    │   └─> Hit: Return cached result
    │
    ├─> L2: Redis Cache (Distributed, 1 hour TTL)
    │   └─> Hit: Return cached result, populate L1
    │
    └─> L3: Database/Vector Store
        └─> Miss: Fetch data, populate L2 and L1
```

#### Components

**9.1 Cache Manager** (`src/cache/cache_manager.py`)

```python
from functools import lru_cache
import redis
import hashlib
import json

class CacheManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.local_cache = {}
        self.max_local_size = 1000
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments."""
        key_data = json.dumps([args, kwargs], sort_keys=True)
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        # Check L1 (local memory)
        if key in self.local_cache:
            return self.local_cache[key]
        
        # Check L2 (Redis)
        value = await self.redis.get(key)
        if value:
            # Populate L1
            self._set_local(key, value)
            return json.loads(value)
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ):
        # Set in L2 (Redis)
        await self.redis.setex(
            key,
            ttl,
            json.dumps(value)
        )
        
        # Set in L1 (local)
        self._set_local(key, value)
    
    def _set_local(self, key: str, value: Any):
        if len(self.local_cache) >= self.max_local_size:
            # Remove oldest item (simple FIFO)
            self.local_cache.pop(next(iter(self.local_cache)))
        self.local_cache[key] = value
```

**9.2 Embedding Cache** (`src/cache/embedding_cache.py`)

```python
class EmbeddingCache:
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.ttl = 86400  # 24 hours
    
    async def get_embedding(
        self,
        text: str,
        model: str
    ) -> Optional[List[float]]:
        key = self.cache._generate_key(
            "embedding",
            text=text,
            model=model
        )
        return await self.cache.get(key)
    
    async def set_embedding(
        self,
        text: str,
        model: str,
        embedding: List[float]
    ):
        key = self.cache._generate_key(
            "embedding",
            text=text,
            model=model
        )
        await self.cache.set(key, embedding, self.ttl)
```

**9.3 Query Result Cache** (`src/cache/query_cache.py`)

```python
class QueryCache:
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.ttl = 3600  # 1 hour
    
    async def get_query_result(
        self,
        question: str,
        document_name: Optional[str],
        top_k: int
    ) -> Optional[QueryResult]:
        key = self.cache._generate_key(
            "query",
            question=question,
            document=document_name,
            top_k=top_k
        )
        cached = await self.cache.get(key)
        if cached:
            return QueryResult(**cached)
        return None
    
    async def set_query_result(
        self,
        question: str,
        document_name: Optional[str],
        top_k: int,
        result: QueryResult
    ):
        key = self.cache._generate_key(
            "query",
            question=question,
            document=document_name,
            top_k=top_k
        )
        await self.cache.set(
            key,
            result.dict(),
            self.ttl
        )
```

**9.4 Connection Pooling**

```python
# Redis connection pool
redis_pool = redis.ConnectionPool(
    host=config.redis_host,
    port=config.redis_port,
    password=config.redis_password,
    max_connections=50,
    decode_responses=True
)

redis_client = redis.Redis(connection_pool=redis_pool)

# HTTP client with connection pooling
import httpx

http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100
    ),
    timeout=httpx.Timeout(30.0)
)
```

**9.5 Request Queuing**

```python
import asyncio
from asyncio import Queue, Semaphore

class RequestQueue:
    def __init__(self, max_concurrent: int = 10):
        self.queue = Queue()
        self.semaphore = Semaphore(max_concurrent)
        self.workers = []
    
    async def process_request(self, request_func, *args, **kwargs):
        async with self.semaphore:
            return await request_func(*args, **kwargs)
    
    async def enqueue(self, request_func, *args, **kwargs):
        return await self.process_request(request_func, *args, **kwargs)
```

#### Cache Invalidation Strategy

```python
class CacheInvalidator:
    @staticmethod
    async def invalidate_document_cache(document_name: str):
        """Invalidate all caches related to a document."""
        # Invalidate query results for this document
        pattern = f"query:*:document:{document_name}:*"
        await redis_client.delete(*await redis_client.keys(pattern))
    
    @staticmethod
    async def invalidate_all_queries():
        """Invalidate all query result caches."""
        pattern = "query:*"
        await redis_client.delete(*await redis_client.keys(pattern))
```

#### Configuration

```python
# .env additions
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_MAX_CONNECTIONS=50

ENABLE_CACHING=true
CACHE_EMBEDDING_TTL=86400
CACHE_QUERY_TTL=3600
LOCAL_CACHE_SIZE=1000

ENABLE_CONNECTION_POOLING=true
HTTP_MAX_CONNECTIONS=100
HTTP_MAX_KEEPALIVE=20

MAX_CONCURRENT_REQUESTS=10
```

#### Performance Benchmarks

Target performance metrics:
- Health check response: < 100ms
- Query with cache hit: < 500ms
- Query with cache miss: < 5s
- Document upload (10 pages): < 30s
- Concurrent requests: 100 req/s per instance



### 10. Data Privacy and Compliance

#### Design Overview

Implement encryption, data retention policies, audit logging, and GDPR compliance features.

#### Components

**10.1 Encryption Service** (`src/security/encryption.py`)

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

class EncryptionService:
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key.encode())
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key."""
        return Fernet.generate_key().decode()
```

**10.2 Data Retention Manager** (`src/compliance/retention.py`)

```python
from datetime import datetime, timedelta
from typing import Dict

class RetentionPolicy:
    POLICIES = {
        "documents": 365,      # days
        "queries": 90,
        "audit_logs": 2555,    # 7 years
        "user_sessions": 30
    }
    
    @staticmethod
    async def apply_retention_policies():
        """Apply retention policies to all data types."""
        for data_type, retention_days in RetentionPolicy.POLICIES.items():
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            await RetentionPolicy._delete_old_data(data_type, cutoff_date)
    
    @staticmethod
    async def _delete_old_data(data_type: str, cutoff_date: datetime):
        """Delete data older than cutoff date."""
        if data_type == "documents":
            # Delete old documents from vector store
            await vector_store.delete_documents_before(cutoff_date)
        elif data_type == "queries":
            # Delete old query logs
            await query_log_db.delete_before(cutoff_date)
        elif data_type == "audit_logs":
            # Archive (don't delete) old audit logs
            await audit_log_db.archive_before(cutoff_date)
```

**10.3 Audit Logger** (`src/compliance/audit_logger.py`)

```python
import hashlib
from datetime import datetime
from typing import Dict, Any

class AuditLogger:
    def __init__(self, storage_backend):
        self.storage = storage_backend
    
    async def log_event(
        self,
        event_type: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        result: str,
        metadata: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None
    ):
        """Log a security-relevant event."""
        event = {
            "event_id": self._generate_event_id(),
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "result": result,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata or {},
            "checksum": None  # Will be calculated
        }
        
        # Calculate checksum for tamper detection
        event["checksum"] = self._calculate_checksum(event)
        
        await self.storage.write(event)
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        return str(uuid.uuid4())
    
    def _calculate_checksum(self, event: Dict) -> str:
        """Calculate checksum for tamper detection."""
        event_copy = event.copy()
        event_copy.pop("checksum", None)
        event_str = json.dumps(event_copy, sort_keys=True)
        return hashlib.sha256(event_str.encode()).hexdigest()
    
    async def verify_integrity(self, event: Dict) -> bool:
        """Verify event has not been tampered with."""
        stored_checksum = event.pop("checksum")
        calculated_checksum = self._calculate_checksum(event)
        return stored_checksum == calculated_checksum

# Usage in API endpoints
@app.post("/upload")
async def upload_document(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    # ... upload logic ...
    
    await audit_logger.log_event(
        event_type="document_upload",
        user_id=current_user.id,
        resource_type="document",
        resource_id=document_id,
        action="create",
        result="success",
        metadata={
            "filename": file.filename,
            "size_bytes": file.size,
            "chunks_created": chunks_created
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
```

**10.4 GDPR Compliance Features**

```python
class GDPRCompliance:
    @staticmethod
    async def export_user_data(user_id: str) -> Dict[str, Any]:
        """Export all data associated with a user (right to data portability)."""
        return {
            "user_profile": await user_db.get_user(user_id),
            "documents": await document_db.get_user_documents(user_id),
            "queries": await query_log_db.get_user_queries(user_id),
            "audit_logs": await audit_log_db.get_user_events(user_id)
        }
    
    @staticmethod
    async def delete_user_data(user_id: str):
        """Delete all data associated with a user (right to be forgotten)."""
        # Delete user documents
        documents = await document_db.get_user_documents(user_id)
        for doc in documents:
            await vector_store.delete_document(doc.id)
            await document_storage.delete(doc.id)
        
        # Anonymize query logs (keep for analytics)
        await query_log_db.anonymize_user_queries(user_id)
        
        # Keep audit logs (legal requirement) but mark user as deleted
        await audit_log_db.mark_user_deleted(user_id)
        
        # Delete user account
        await user_db.delete_user(user_id)
    
    @staticmethod
    async def get_consent_status(user_id: str) -> Dict[str, bool]:
        """Get user's consent status for various data processing activities."""
        return await consent_db.get_user_consents(user_id)
    
    @staticmethod
    async def update_consent(
        user_id: str,
        consent_type: str,
        granted: bool
    ):
        """Update user's consent for data processing."""
        await consent_db.update_consent(user_id, consent_type, granted)
        
        # Log consent change
        await audit_logger.log_event(
            event_type="consent_change",
            user_id=user_id,
            resource_type="consent",
            resource_id=consent_type,
            action="update",
            result="success",
            metadata={"granted": granted}
        )
```

**10.5 Data Classification**

```python
from enum import Enum

class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class DataClassifier:
    @staticmethod
    def classify_document(content: str) -> DataClassification:
        """Automatically classify document sensitivity."""
        # Check for PII patterns
        if DataClassifier._contains_pii(content):
            return DataClassification.CONFIDENTIAL
        
        # Check for sensitive keywords
        if DataClassifier._contains_sensitive_keywords(content):
            return DataClassification.INTERNAL
        
        return DataClassification.PUBLIC
    
    @staticmethod
    def _contains_pii(content: str) -> bool:
        """Check if content contains PII."""
        pii_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
        ]
        for pattern in pii_patterns:
            if re.search(pattern, content):
                return True
        return False
```

#### API Endpoints

```python
@app.get("/gdpr/export")
async def export_user_data(
    current_user: User = Depends(get_current_user)
):
    """Export all user data (GDPR Article 20)."""
    data = await GDPRCompliance.export_user_data(current_user.id)
    return JSONResponse(content=data)

@app.delete("/gdpr/delete")
async def delete_user_data(
    current_user: User = Depends(get_current_user)
):
    """Delete all user data (GDPR Article 17)."""
    await GDPRCompliance.delete_user_data(current_user.id)
    return {"message": "User data deletion initiated"}

@app.get("/gdpr/consents")
async def get_consents(
    current_user: User = Depends(get_current_user)
):
    """Get user consent status."""
    return await GDPRCompliance.get_consent_status(current_user.id)

@app.put("/gdpr/consents/{consent_type}")
async def update_consent(
    consent_type: str,
    granted: bool,
    current_user: User = Depends(get_current_user)
):
    """Update user consent."""
    await GDPRCompliance.update_consent(
        current_user.id,
        consent_type,
        granted
    )
    return {"message": "Consent updated"}
```

#### Configuration

```python
# .env additions
ENCRYPTION_KEY=<generated-key>
ENABLE_ENCRYPTION_AT_REST=true
ENABLE_AUDIT_LOGGING=true
AUDIT_LOG_STORAGE=postgresql://...
DATA_RETENTION_DAYS_DOCUMENTS=365
DATA_RETENTION_DAYS_QUERIES=90
DATA_RETENTION_DAYS_AUDIT_LOGS=2555
ENABLE_GDPR_FEATURES=true
```



### 11. Backup and Disaster Recovery

#### Design Overview

Implement automated backup procedures with point-in-time recovery and disaster recovery testing.

#### Backup Architecture

```
┌─────────────────────────────────────────────┐
│         Production Environment              │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Vector   │  │ Document │  │ Metadata │ │
│  │  Store   │  │ Storage  │  │    DB    │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │             │             │        │
└───────┼─────────────┼─────────────┼────────┘
        │             │             │
        ▼             ▼             ▼
┌─────────────────────────────────────────────┐
│         Backup Service (Cron Jobs)          │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  Daily Full Backup (2 AM UTC)        │  │
│  │  Hourly Incremental (Business Hours) │  │
│  │  Weekly Archive (Sunday)             │  │
│  └──────────────────────────────────────┘  │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│      Backup Storage (S3/GCS)                │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Daily   │  │  Weekly  │  │ Monthly  │ │
│  │ (30 days)│  │(12 weeks)│  │(12 months│ │
│  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────┘
```

#### Components

**11.1 Backup Manager** (`src/backup/backup_manager.py`)

```python
from datetime import datetime, timedelta
import boto3
import tarfile
import tempfile

class BackupManager:
    def __init__(self, config):
        self.config = config
        self.s3_client = boto3.client('s3')
        self.backup_bucket = config.backup_bucket
    
    async def create_full_backup(self) -> str:
        """Create a full backup of all system data."""
        backup_id = f"full-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = f"{temp_dir}/{backup_id}"
            os.makedirs(backup_path)
            
            # Backup vector store
            await self._backup_vector_store(backup_path)
            
            # Backup document storage
            await self._backup_documents(backup_path)
            
            # Backup metadata database
            await self._backup_metadata(backup_path)
            
            # Create manifest
            manifest = self._create_manifest(backup_id)
            with open(f"{backup_path}/manifest.json", 'w') as f:
                json.dump(manifest, f)
            
            # Create tarball
            tarball_path = f"{temp_dir}/{backup_id}.tar.gz"
            with tarfile.open(tarball_path, "w:gz") as tar:
                tar.add(backup_path, arcname=backup_id)
            
            # Upload to S3
            await self._upload_to_s3(tarball_path, backup_id)
            
            # Verify backup integrity
            await self._verify_backup(backup_id)
            
            logger.info(f"Full backup created: {backup_id}")
            return backup_id
    
    async def _backup_vector_store(self, backup_path: str):
        """Backup vector store data."""
        if config.vector_store_backend == "qdrant":
            # Create Qdrant snapshot
            snapshot = await qdrant_client.create_snapshot(
                collection_name=config.qdrant_collection_name
            )
            # Download snapshot
            snapshot_data = await qdrant_client.download_snapshot(
                collection_name=config.qdrant_collection_name,
                snapshot_name=snapshot.name
            )
            with open(f"{backup_path}/vector_store.snapshot", 'wb') as f:
                f.write(snapshot_data)
        else:
            # Copy FAISS index files
            shutil.copy(config.vector_store_path, backup_path)
            shutil.copy(config.metadata_path, backup_path)
    
    async def _backup_documents(self, backup_path: str):
        """Backup document files."""
        # List all documents in S3
        documents = await document_storage.list_all()
        
        doc_backup_path = f"{backup_path}/documents"
        os.makedirs(doc_backup_path)
        
        for doc in documents:
            doc_data = await document_storage.download(doc.id)
            with open(f"{doc_backup_path}/{doc.id}.pdf", 'wb') as f:
                f.write(doc_data)
    
    async def _backup_metadata(self, backup_path: str):
        """Backup metadata database."""
        # Export database to SQL dump
        dump_path = f"{backup_path}/metadata.sql"
        await db.export_to_file(dump_path)
    
    def _create_manifest(self, backup_id: str) -> Dict:
        """Create backup manifest with metadata."""
        return {
            "backup_id": backup_id,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "full",
            "version": "1.0",
            "components": {
                "vector_store": {
                    "backend": config.vector_store_backend,
                    "document_count": vector_store.get_document_count()
                },
                "documents": {
                    "count": document_storage.count()
                },
                "metadata": {
                    "size_bytes": os.path.getsize(f"{backup_path}/metadata.sql")
                }
            }
        }
    
    async def _upload_to_s3(self, file_path: str, backup_id: str):
        """Upload backup to S3."""
        s3_key = f"backups/{backup_id}.tar.gz"
        
        with open(file_path, 'rb') as f:
            self.s3_client.upload_fileobj(
                f,
                self.backup_bucket,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'StorageClass': 'STANDARD_IA'
                }
            )
    
    async def _verify_backup(self, backup_id: str):
        """Verify backup integrity."""
        s3_key = f"backups/{backup_id}.tar.gz"
        
        # Check file exists
        try:
            self.s3_client.head_object(
                Bucket=self.backup_bucket,
                Key=s3_key
            )
        except:
            raise BackupVerificationError(f"Backup {backup_id} not found in S3")
        
        # Verify checksum
        # Download and extract manifest
        # Verify all components present
```

**11.2 Restore Manager** (`src/backup/restore_manager.py`)

```python
class RestoreManager:
    def __init__(self, config):
        self.config = config
        self.s3_client = boto3.client('s3')
        self.backup_bucket = config.backup_bucket
    
    async def restore_from_backup(
        self,
        backup_id: str,
        target_environment: str = "staging"
    ):
        """Restore system from backup."""
        logger.info(f"Starting restore from backup: {backup_id}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download backup from S3
            backup_path = await self._download_from_s3(backup_id, temp_dir)
            
            # Extract tarball
            extract_path = f"{temp_dir}/extracted"
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(extract_path)
            
            # Read manifest
            with open(f"{extract_path}/{backup_id}/manifest.json") as f:
                manifest = json.load(f)
            
            # Restore vector store
            await self._restore_vector_store(
                f"{extract_path}/{backup_id}",
                manifest
            )
            
            # Restore documents
            await self._restore_documents(
                f"{extract_path}/{backup_id}",
                manifest
            )
            
            # Restore metadata
            await self._restore_metadata(
                f"{extract_path}/{backup_id}",
                manifest
            )
            
            # Verify restore
            await self._verify_restore(manifest)
            
            logger.info(f"Restore completed: {backup_id}")
    
    async def list_available_backups(self) -> List[Dict]:
        """List all available backups."""
        response = self.s3_client.list_objects_v2(
            Bucket=self.backup_bucket,
            Prefix="backups/"
        )
        
        backups = []
        for obj in response.get('Contents', []):
            backups.append({
                "backup_id": obj['Key'].split('/')[-1].replace('.tar.gz', ''),
                "timestamp": obj['LastModified'],
                "size_bytes": obj['Size']
            })
        
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
    
    async def get_point_in_time_backup(
        self,
        target_datetime: datetime
    ) -> Optional[str]:
        """Find the closest backup to a specific point in time."""
        backups = await self.list_available_backups()
        
        closest_backup = None
        min_diff = timedelta.max
        
        for backup in backups:
            diff = abs(backup['timestamp'] - target_datetime)
            if diff < min_diff:
                min_diff = diff
                closest_backup = backup['backup_id']
        
        return closest_backup
```

**11.3 Backup Scheduler** (`scripts/backup_scheduler.py`)

```python
import schedule
import time

def schedule_backups():
    # Daily full backup at 2 AM UTC
    schedule.every().day.at("02:00").do(
        lambda: asyncio.run(backup_manager.create_full_backup())
    )
    
    # Hourly incremental during business hours (9 AM - 6 PM UTC)
    for hour in range(9, 18):
        schedule.every().day.at(f"{hour:02d}:00").do(
            lambda: asyncio.run(backup_manager.create_incremental_backup())
        )
    
    # Weekly archive on Sunday
    schedule.every().sunday.at("03:00").do(
        lambda: asyncio.run(backup_manager.create_archive_backup())
    )
    
    # Cleanup old backups daily
    schedule.every().day.at("04:00").do(
        lambda: asyncio.run(backup_manager.cleanup_old_backups())
    )
    
    while True:
        schedule.run_pending()
        time.sleep(60)
```

**11.4 Disaster Recovery Testing**

```python
class DRTester:
    async def run_dr_test(self):
        """Run disaster recovery test."""
        logger.info("Starting DR test")
        
        # 1. Create test backup
        backup_id = await backup_manager.create_full_backup()
        
        # 2. Restore to staging environment
        await restore_manager.restore_from_backup(
            backup_id,
            target_environment="staging"
        )
        
        # 3. Run validation tests
        validation_results = await self._run_validation_tests()
        
        # 4. Generate DR test report
        report = self._generate_dr_report(validation_results)
        
        logger.info(f"DR test completed: {report['status']}")
        return report
    
    async def _run_validation_tests(self) -> Dict:
        """Run validation tests on restored environment."""
        results = {
            "document_count": await self._verify_document_count(),
            "vector_store": await self._verify_vector_store(),
            "query_functionality": await self._verify_query_functionality(),
            "data_integrity": await self._verify_data_integrity()
        }
        return results
```

#### Configuration

```python
# .env additions
ENABLE_BACKUPS=true
BACKUP_BUCKET=docqa-backups
BACKUP_SCHEDULE_DAILY=02:00
BACKUP_RETENTION_DAYS=30
BACKUP_RETENTION_WEEKS=12
BACKUP_RETENTION_MONTHS=12
ENABLE_DR_TESTING=true
DR_TEST_SCHEDULE=monthly
```

