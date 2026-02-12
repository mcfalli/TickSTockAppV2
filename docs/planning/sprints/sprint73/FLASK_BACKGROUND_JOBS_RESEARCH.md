# Sprint 73 Research: Flask Background Job Patterns

**Date**: February 11, 2026  
**Context**: Foundation research for Sprint 73 - Data Maintenance Background Jobs API  
**Status**: Complete

## 1. Flask Threading & Application Context

### 1.1 Official Flask Documentation

**Key Resources**:
- [The Application Context — Flask Documentation (3.1.x)](https://flask.palletsprojects.com/en/stable/appcontext/)
- [The Request Context — Flask Documentation (3.1.x)](https://flask.palletsprojects.com/en/stable/reqcontext/)
- [Design Decisions in Flask — Flask Documentation (3.1.x)](https://flask.palletsprojects.com/en/stable/design/)

**Core Concepts**:
1. **Application Context is Thread-Local**: The application context is tied to each thread and cannot be accessed from another thread—Flask raises an exception if you try
2. **Request Context is Also Thread-Local**: Requests are thread-local and cannot be passed to another thread
3. **Context-Local Objects**: Flask uses context-locals (implemented in Werkzeug) to provide thread-safe, thread-unique access to data like `current_app`, `g`, and request data

### 1.2 Using Threading with Flask

**Pattern for Background Tasks**:

```python
from flask import current_app
import threading

def background_task():
    # Must push application context when running outside a request
    with app.app_context():
        # Now current_app, g, logger are accessible
        current_app.logger.info("Background task running")
        # Access database, configuration, etc.

# Start background thread
thread = threading.Thread(target=background_task)
thread.start()
```

**Critical Gotcha**: You MUST pass the Flask app object to the thread function, NOT the `current_app` proxy:

```python
# WRONG - current_app is thread-local and won't work in another thread
def task():
    with current_app.app_context():  # RuntimeError!
        pass

# CORRECT - pass app object, then push context
def task(app):
    with app.app_context():
        pass

thread = threading.Thread(target=task, args=(app,))
```

**Advanced Reference**:
- [Deep Dive into Flask's Application and Request Contexts | TestDriven.io](https://testdriven.io/blog/flask-contexts-advanced/)
- [How the Application and Request Contexts Work in Python Flask | AppSignal Blog](https://blog.appsignal.com/2025/07/23/how-the-application-and-request-contexts-work-in-flask.html)
- [Using Threads with Flask — Michael Toohig](https://michaeltoohig.com/blog/using-threads-with-flask/)
- [Flask Discussion: Accessing flask.g and flask.current_app in a threading.Thread](https://github.com/pallets/flask/discussions/5505)

### 1.3 Thread-Local Storage Deep Dive

[Thread Safety | imdeepmind](https://imdeepmind.com/docs/frameworks-libraries/backend/flask/thread-safety/)

**How Flask Implements Thread Safety**:
- Flask uses context-local objects (thread-local wrapper from Werkzeug)
- Each thread gets its own independent data when accessing context-local objects
- The `g` object is thread-local: different threads accessing `g` get their own instances
- This is "thread-safe and thread-unique": safe for concurrent access + unique per-thread data

**Example of Thread Isolation**:
```python
# Thread 1
with app.app_context():
    g.user_id = 123
    
# Thread 2
with app.app_context():
    g.user_id = 456
    
# Each thread sees its own g.user_id value
```

## 2. Python Threading & GIL

### 2.1 The Global Interpreter Lock (GIL)

**Key Resources**:
- [What Is the Python Global Interpreter Lock (GIL)? – Real Python](https://realpython.com/python-gil/)
- [GlobalInterpreterLock - Python Wiki](https://wiki.python.org/moin/GlobalInterpreterLock/)
- [Python behind the scenes #13: the GIL and its effects on Python multithreading](https://tenthousandmeters.com/blog/python-behind-the-scenes-13-the-gil-and-its-effects-on-python-multithreading/)

**Core Facts**:
1. The GIL is a single lock on the Python interpreter that allows only one thread to execute Python bytecode at a time
2. **For I/O-bound tasks**: Threading works well because threads release the GIL during I/O operations (network, disk, database)
3. **For CPU-bound tasks**: Threading provides no speedup (use multiprocessing instead)

### 2.2 Threading Best Practices

**When to Use Threading**:
- I/O-bound operations: database queries, HTTP requests, file I/O, Redis operations
- Background job execution (fits TickStock's data maintenance jobs)
- Ideal for Flask background tasks since Flask typically does I/O operations

**When NOT to Use Threading**:
- CPU-intensive operations (use multiprocessing)
- Operations requiring true parallelism across CPU cores

**Recommendation for TickStock**: Threading is appropriate for data maintenance jobs which are primarily I/O-bound (database reads/writes, API calls)

### 2.3 Locks & Shared State

**Key Resource**: [Python Multithreading & the GIL: Are Locks Still Necessary?](https://www.pythontutorials.net/blog/are-locks-unnecessary-in-multi-threaded-python-code-because-of-the-gil/)

**Important**: Even though the GIL exists, locks are still necessary:
- The GIL protects the interpreter, NOT your data
- High-level operations (like incrementing a counter) decompose into multiple bytecode instructions
- These operations can be interrupted, causing race conditions

**Shared State Pattern**:
```python
# BAD - Race condition even with GIL
counter = 0

def increment():
    global counter
    counter += 1  # Decomposes to 3 bytecode instructions!
```

**Safe Shared State Pattern (Producer-Consumer)**:
```python
import queue

# Thread-safe by design
job_queue = queue.Queue()

# Producer thread
job_queue.put({"task": "load_etf_holdings"})

# Consumer thread
job = job_queue.get()  # Blocks until job available
```

**Best Practice**: Use `queue.Queue` (thread-safe) instead of managing locks on shared state for job management

## 3. Database Thread Safety (SQLAlchemy)

### 3.1 Session Thread Safety Issue

**Key Resources**:
- [Flask db.session is not thread-safe (scheduled tasks)](https://github.com/RiotGames/cloud-inquisitor/issues/6)
- [Creating thread safe and managed sessions using SQLAlchemy](https://gist.github.com/nitred/4323d86bb22b7ec788a8dcfcac03b27a)
- [SQLAlchemy Contextual/Thread-local Sessions (v2.1)](https://docs.sqlalchemy.org/en/21/orm/contextual.html)
- [Multi-thread safety in Flask-SQLAlchemy database connection pool](https://www.programmerall.com/article/6561410742/)

**Critical Issue**:
- SQLAlchemy Session objects are NOT thread-safe
- Connection objects are NOT thread-safe
- Concurrent usage of a Session in multiple threads causes race conditions
- db.session is a global session—must not be shared between threads

### 3.2 Solution: Scoped Sessions

**Best Practice**:
```python
from sqlalchemy.orm import scoped_session, sessionmaker

# Create a scoped session (uses thread-local storage)
db_session = scoped_session(sessionmaker(bind=engine))

# Each thread gets its own session
def background_task(app):
    with app.app_context():
        # Flask-SQLAlchemy will use thread-local session
        from models import Stock
        Stock.query.filter_by(symbol='AAPL').first()
```

**Key Points**:
- Flask-SQLAlchemy uses scoped sessions automatically
- Each thread automatically gets its own session
- Sessions are isolated and thread-safe
- Dispose of sessions when thread work completes (Flask handles this)

**Pattern for Background Threads**:
```python
from flask import current_app
from src.models import db

def background_task(app):
    with app.app_context():
        # Flask-SQLAlchemy session is thread-local
        try:
            result = db.session.query(MyModel).first()
        finally:
            # Session is automatically cleaned up when context exits
            pass
```

## 4. Async Job Submission Pattern (202 Accepted)

### 4.1 HTTP Status 202 Accepted

**Key Resources**:
- [REST API Design for Long-Running Tasks](https://restfulapi.net/rest-api-design-for-long-running-tasks/)
- [HTTP Status 202 (Accepted) - REST API Tutorial](https://restfulapi.net/http-status-202-accepted/)
- [Why Your REST API Should Return 202 Instead of 200](https://blog.kvmpods.com/why-your-rest-api-should-return-202-instead-of-200/)
- [Asynchronous Request-Reply pattern - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/async-request-reply)

**When to Use 202**:
- The request has been accepted for processing
- Processing has NOT been completed
- Client needs to poll or use callbacks for results
- **Perfect for TickStock data maintenance jobs**

**Standard Response Format**:
```json
POST /api/data-maintenance/load-etf-holdings
Content-Type: application/json

Status: 202 Accepted
Location: /api/jobs/12345
Retry-After: 5

{
  "job_id": "12345",
  "status": "pending",
  "message": "Job accepted for processing",
  "polling_url": "/api/jobs/12345"
}
```

### 4.2 Polling Status Endpoint Pattern

**Flow**:
```
1. POST /api/jobs → 202 Accepted + Location header
2. GET /api/jobs/{id} → 200 OK with status
3. While status != 'completed':
     GET /api/jobs/{id} → 200 OK with progress
4. Status becomes 'completed':
     GET /api/jobs/{id} → 200 OK with result or redirect
```

**Status Response Example** (Still Processing):
```json
GET /api/jobs/12345

Status: 200 OK
Retry-After: 5

{
  "job_id": "12345",
  "status": "in_progress",
  "percentage": 45,
  "message": "Processed 450 of 1000 symbols",
  "started_at": "2026-02-11T10:30:00Z",
  "updated_at": "2026-02-11T10:35:23Z"
}
```

**Status Response Example** (Completed):
```json
GET /api/jobs/12345

Status: 200 OK

{
  "job_id": "12345",
  "status": "completed",
  "result": {
    "symbols_processed": 1000,
    "duration_seconds": 45.5,
    "errors": 0
  },
  "completed_at": "2026-02-11T10:35:45Z"
}
```

**Status Response Example** (Failed):
```json
GET /api/jobs/12345

Status: 200 OK

{
  "job_id": "12345",
  "status": "failed",
  "error": "Database connection timeout",
  "error_details": "Could not acquire database connection after 30s",
  "started_at": "2026-02-11T10:30:00Z",
  "failed_at": "2026-02-11T10:31:15Z"
}
```

### 4.3 Retry-After Header Best Practices

[REST API Design for Long-Running Tasks](https://restfulapi.net/rest-api-design-for-long-running-tasks/)

**Purpose**: Guides clients on optimal polling interval

**Format Options**:
```
# Delay in seconds
Retry-After: 5

# HTTP date (e.g., when to retry)
Retry-After: Wed, 11 Feb 2026 11:00:00 GMT
```

**Strategy**:
- Start with short interval (e.g., 2-5 seconds)
- Increase interval as job progresses if percentages indicate long duration
- Maximum reasonable interval: 60 seconds

## 5. Flask Background Job Implementation Patterns

### 5.1 Simple Threading Pattern

```python
# app.py
from flask import Blueprint, request, jsonify, current_app
from src.models import db
import threading
import uuid
from datetime import datetime

jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')

# Simple in-memory job store (replace with database for production)
job_store = {}
job_lock = threading.Lock()

def background_worker(app, job_id, task_func, *args, **kwargs):
    """Execute task in thread with proper Flask context"""
    try:
        with app.app_context():
            with job_lock:
                job_store[job_id]['status'] = 'in_progress'
                job_store[job_id]['started_at'] = datetime.utcnow().isoformat()
            
            # Execute task
            result = task_func(*args, **kwargs)
            
            with job_lock:
                job_store[job_id]['status'] = 'completed'
                job_store[job_id]['result'] = result
                job_store[job_id]['completed_at'] = datetime.utcnow().isoformat()
    
    except Exception as e:
        with job_lock:
            job_store[job_id]['status'] = 'failed'
            job_store[job_id]['error'] = str(e)
            job_store[job_id]['failed_at'] = datetime.utcnow().isoformat()
        current_app.logger.exception(f"Job {job_id} failed")

@jobs_bp.route('/load-etf-holdings', methods=['POST'])
def submit_load_etf_holdings():
    """Submit ETF holdings load job"""
    job_id = str(uuid.uuid4())
    
    with job_lock:
        job_store[job_id] = {
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'type': 'load_etf_holdings'
        }
    
    # Start background thread
    thread = threading.Thread(
        target=background_worker,
        args=(current_app._get_current_object(), job_id, load_etf_holdings)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'pending',
        'polling_url': f'/api/jobs/{job_id}'
    }), 202

@jobs_bp.route('/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Check job status"""
    with job_lock:
        if job_id not in job_store:
            return jsonify({'error': 'Job not found'}), 404
        
        job = job_store[job_id].copy()
    
    response = {
        'job_id': job_id,
        'status': job['status'],
    }
    
    # Include relevant fields based on status
    if job['status'] == 'in_progress':
        response['percentage'] = job.get('percentage', 0)
        response['message'] = job.get('message', 'Processing')
    elif job['status'] == 'completed':
        response['result'] = job.get('result')
    elif job['status'] == 'failed':
        response['error'] = job['error']
    
    # Add timestamps
    for key in ['created_at', 'started_at', 'completed_at', 'failed_at']:
        if key in job:
            response[key] = job[key]
    
    return jsonify(response), 200

def load_etf_holdings():
    """Background task: load ETF holdings"""
    # Task implementation
    return {'symbols_processed': 1000}

# Register blueprint
app.register_blueprint(jobs_bp)
```

### 5.2 Critical: App Object in Threading

**WRONG**:
```python
thread = threading.Thread(
    target=background_worker,
    args=(current_app,)  # WRONG - current_app is thread-local proxy
)
```

**CORRECT**:
```python
thread = threading.Thread(
    target=background_worker,
    args=(current_app._get_current_object(), job_id, task_func)  # Use _get_current_object()
)
# OR
thread = threading.Thread(
    target=background_worker,
    args=(app, job_id, task_func)  # Pass app object directly
)
```

### 5.3 Production Pattern: Task Queue (RQ/Celery)

**Key Resource**: [The Flask Mega-Tutorial, Part XXII: Background Jobs](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xxii-background-jobs)

For production TickStock, consider Redis Queue (RQ) or Celery:

**RQ Pattern**:
```python
from redis import Redis
from rq import Queue
from flask import current_app

@jobs_bp.route('/load-etf-holdings', methods=['POST'])
def submit_load_etf_holdings():
    with Connection(redis.from_url(current_app.config['REDIS_URL'])):
        q = Queue()
        job = q.enqueue(load_etf_holdings)
    
    return jsonify({
        'job_id': job.get_id(),
        'status': 'queued'
    }), 202
```

**Advantages**:
- Separate worker processes (no GIL contention)
- Persistent job queue (survives restarts)
- Built-in retry logic
- Redis monitoring

**When to Use**:
- Production deployments
- High-volume job processing
- Need for distributed workers

## 6. Job Status Storage

### 6.1 In-Memory (Development Only)

**Pros**: Simple, fast
**Cons**: Lost on restart, not scalable
**Use Case**: Local development, temporary proof-of-concept

```python
job_store = {}
job_lock = threading.Lock()
```

### 6.2 Redis (Recommended for TickStock)

**Advantages**:
- Persistent (survives restarts)
- Atomic operations (built-in thread safety)
- Already integrated with TickStock (Redis Pub-Sub)
- Compatible with worker scaling
- Fast access (<10ms)

**Pattern**:
```python
import redis
import json

redis_client = redis.Redis.from_url(current_app.config['REDIS_URL'])

def store_job_status(job_id, status_dict):
    """Store job status in Redis"""
    redis_client.set(
        f'job:{job_id}',
        json.dumps(status_dict),
        ex=86400  # 24-hour expiration
    )

def get_job_status(job_id):
    """Retrieve job status from Redis"""
    data = redis_client.get(f'job:{job_id}')
    return json.loads(data) if data else None
```

### 6.3 Database (SQL)

**Advantages**:
- Persistent, queryable
- Historical records
- Complex filtering

**Disadvantages**:
- Slower than Redis for frequent updates
- Requires migrations

**Consider for**: Long-term job history, audit trails

## 7. Progress Tracking Patterns

### 7.1 Percentage Progress

```python
def load_etf_holdings(app, job_id):
    """Load ETF holdings with progress tracking"""
    etfs = ['SPY', 'QQQ', 'DIA']  # 3 ETFs
    
    for idx, etf in enumerate(etfs):
        # Load ETF holdings
        holdings = api.get_etf_holdings(etf)
        
        # Update progress
        percentage = ((idx + 1) / len(etfs)) * 100
        update_job_progress(job_id, percentage, f"Processed {etf}")
        
        time.sleep(0.1)  # Simulate work
    
    return {'etfs_processed': len(etfs)}

def update_job_progress(job_id, percentage, message):
    """Update job progress in Redis"""
    data = redis_client.get(f'job:{job_id}')
    status = json.loads(data) if data else {}
    status.update({
        'percentage': percentage,
        'message': message,
        'updated_at': datetime.utcnow().isoformat()
    })
    redis_client.set(f'job:{job_id}', json.dumps(status), ex=86400)
```

### 7.2 Item Count Progress

```python
def load_etf_holdings(app, job_id, etf_name):
    """Load ETF holdings with item count"""
    api = MassiveAPI()
    holdings = api.get_etf_holdings(etf_name)
    
    for idx, symbol in enumerate(holdings):
        # Process symbol
        process_symbol(symbol)
        
        if idx % 10 == 0:  # Update every 10 symbols
            update_job_progress(job_id, {
                'items_processed': idx + 1,
                'total_items': len(holdings),
                'percentage': ((idx + 1) / len(holdings)) * 100
            })
```

## 8. Error Handling & Cleanup

### 8.1 Exception Handling Pattern

```python
def background_worker(app, job_id, task_func, *args):
    """Worker with error handling"""
    try:
        with app.app_context():
            update_job_progress(job_id, {'status': 'in_progress'})
            result = task_func(job_id, *args)
            update_job_progress(job_id, {
                'status': 'completed',
                'result': result,
                'completed_at': datetime.utcnow().isoformat()
            })
    
    except ValueError as e:
        # Validation errors - client's fault
        current_app.logger.warning(f"Job {job_id} validation error: {e}")
        update_job_progress(job_id, {
            'status': 'failed',
            'error': str(e),
            'error_type': 'validation'
        })
    
    except Exception as e:
        # Unexpected errors
        current_app.logger.exception(f"Job {job_id} failed unexpectedly")
        update_job_progress(job_id, {
            'status': 'failed',
            'error': f"Internal error: {str(e)}",
            'error_type': 'system'
        })
```

### 8.2 Resource Cleanup

```python
from contextlib import contextmanager

@contextmanager
def job_cleanup(app, job_id):
    """Ensure cleanup even if task fails"""
    try:
        with app.app_context():
            yield
    finally:
        # Clean up resources
        current_app.logger.info(f"Cleaned up job {job_id}")

def background_worker(app, job_id, task_func):
    with job_cleanup(app, job_id):
        result = task_func(job_id)
```

## 9. Common Gotchas & Solutions

### 9.1 Gotcha: Application Context in Threading

**Problem**:
```python
def task():
    with current_app.app_context():  # RuntimeError!
        pass
```

**Solution**:
```python
def task(app):
    with app.app_context():
        pass

thread = threading.Thread(target=task, args=(app,))
```

### 9.2 Gotcha: Daemon vs Non-Daemon Threads

**Daemon Threads**:
```python
thread = threading.Thread(target=task)
thread.daemon = True  # Exit when main thread exits
thread.start()
```

**Problem**: Long-running jobs interrupted on shutdown

**Solution for Data Maintenance**:
```python
thread = threading.Thread(target=task)
thread.daemon = False  # Run to completion
thread.start()

# Or track threads and wait for completion
active_threads = set()
active_threads.add(thread)

# On shutdown:
for thread in active_threads:
    thread.join(timeout=300)  # Wait up to 5 minutes
```

### 9.3 Gotcha: Thread-Local Session Reuse

**Problem**:
```python
# WRONG - Each transaction should have its own session
db.session.execute(...)
thread.start()  # Thread inherits parent's session
```

**Solution**: Flask-SQLAlchemy handles this automatically with scoped sessions

### 9.4 Gotcha: Job ID Generation

**Problem**: Simple counter not thread-safe
```python
job_counter = 0

def generate_job_id():
    global job_counter
    job_counter += 1  # Race condition!
    return job_counter
```

**Solution**: Use uuid
```python
import uuid
job_id = str(uuid.uuid4())
```

### 9.5 Gotcha: Memory Leaks from In-Memory Job Store

**Problem**:
```python
job_store = {}  # Grows indefinitely
```

**Solution**: Use Redis with TTL or database with cleanup job

```python
# Redis with expiration
redis_client.set(f'job:{job_id}', json.dumps(status), ex=86400)

# Database cleanup (daily)
@app.cli.command('cleanup-old-jobs')
def cleanup_old_jobs():
    cutoff = datetime.utcnow() - timedelta(days=7)
    Job.query.filter(Job.created_at < cutoff).delete()
    db.session.commit()
```

## 10. Recommended Architecture for TickStock Sprint 73

### 10.1 Hybrid Approach

**For Immediate Implementation**:
1. **Job Submission**: 202 Accepted pattern with Location header
2. **Job Storage**: Redis (leverages existing infrastructure)
3. **Job Execution**: Threading (simple, sufficient for I/O-bound tasks)
4. **Status Polling**: Standard REST endpoint with Retry-After header

**Code Structure**:
```
src/
  services/
    data_maintenance_service.py      # Business logic (load_etf_holdings, etc.)
  api/
    data_maintenance_routes.py        # Flask Blueprint (POST /jobs, GET /jobs/{id})
  models/
    jobs.py                           # Job status schema (Pydantic for validation)
  workers/
    job_worker.py                     # Threading worker with context management
```

### 10.2 Database Tables

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failed_at TIMESTAMP,
    error_message TEXT,
    result_json JSONB,
    created_by VARCHAR(255),
    INDEX (status, created_at),
    INDEX (created_at)
);

CREATE TABLE job_progress (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id),
    percentage INTEGER,
    message TEXT,
    updated_at TIMESTAMP NOT NULL,
    INDEX (job_id, updated_at)
);
```

### 10.3 Configuration (.env)

```bash
# Job processing
JOB_STORE_BACKEND=redis  # redis|database|memory
JOB_EXPIRATION_HOURS=24  # Job metadata retention
JOB_MAX_CONCURRENT=3     # Max threads for data maintenance
JOB_PROGRESS_UPDATE_INTERVAL=5  # Seconds between progress updates
JOB_TIMEOUT_SECONDS=3600  # 1 hour max per job

# Polling recommendations
CLIENT_RETRY_AFTER_INITIAL=5   # Seconds
CLIENT_RETRY_AFTER_MAX=60      # Seconds
```

## 11. Testing Patterns

### 11.1 Unit Testing Background Tasks

```python
import pytest
from unittest.mock import patch, MagicMock

def test_load_etf_holdings_success(app):
    """Test successful ETF holdings load"""
    with app.app_context():
        with patch('src.services.data_maintenance_service.api') as mock_api:
            mock_api.get_etf_holdings.return_value = ['AAPL', 'MSFT']
            
            result = load_etf_holdings('2026-02-11')
            
            assert result['etfs_processed'] == 1
            assert result['symbols_processed'] == 2

def test_background_worker_context(app):
    """Test worker properly manages Flask context"""
    job_id = 'test-job'
    task_called = []
    
    def mock_task(jid):
        # Verify context is available
        assert current_app is not None
        task_called.append(True)
    
    worker_thread = threading.Thread(
        target=background_worker,
        args=(app, job_id, mock_task)
    )
    worker_thread.start()
    worker_thread.join(timeout=5)
    
    assert task_called
```

### 11.2 Integration Testing

```python
def test_job_submission_and_polling(client):
    """Test complete job workflow"""
    # 1. Submit job
    response = client.post('/api/jobs/load-etf-holdings')
    assert response.status_code == 202
    job_id = response.json['job_id']
    
    # 2. Check initial status
    response = client.get(f'/api/jobs/{job_id}')
    assert response.status_code == 200
    assert response.json['status'] in ['pending', 'in_progress']
    
    # 3. Wait for completion
    for _ in range(60):
        response = client.get(f'/api/jobs/{job_id}')
        if response.json['status'] == 'completed':
            break
        time.sleep(1)
    
    assert response.json['status'] == 'completed'
    assert 'result' in response.json
```

## References Summary

### Flask Documentation
- [The Application Context — Flask (3.1.x)](https://flask.palletsprojects.com/en/stable/appcontext/)
- [The Request Context — Flask (3.1.x)](https://flask.palletsprojects.com/en/stable/reqcontext/)
- [Background Tasks with Celery — Flask Patterns](https://flask.palletsprojects.com/en/stable/patterns/celery/)

### Flask Blog Posts & Tutorials
- [The Flask Mega-Tutorial, Part XXII: Background Jobs - Miguel Grinberg](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xxii-background-jobs)
- [Deep Dive into Flask's Application and Request Contexts - TestDriven.io](https://testdriven.io/blog/flask-contexts-advanced/)
- [Using Threads with Flask — Michael Toohig](https://michaeltoohig.com/blog/using-threads-with-flask/)

### Python Threading & GIL
- [What Is the Python Global Interpreter Lock (GIL)? – Real Python](https://realpython.com/python-gil/)
- [Python behind the scenes #13: the GIL and its effects on Python multithreading](https://tenthousandmeters.com/blog/python-behind-the-scenes-13-the-gil-and-its-effects-on-python-multithreading/)

### REST API Patterns
- [REST API Design for Long-Running Tasks](https://restfulapi.net/rest-api-design-for-long-running-tasks/)
- [HTTP Status 202 (Accepted) - REST API Tutorial](https://restfulapi.net/http-status-202-accepted/)
- [Asynchronous Request-Reply pattern - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/async-request-reply)

### Database & Threading
- [SQLAlchemy Contextual/Thread-local Sessions (v2.1)](https://docs.sqlalchemy.org/en/21/orm/contextual.html)
- [Flask db.session is not thread-safe - GitHub Issue](https://github.com/RiotGames/cloud-inquisitor/issues/6)

---

**Document Status**: Complete - Ready for Sprint 73 PRP Creation  
**Last Updated**: February 11, 2026  
**Next Step**: Use this research as foundation for `/prp-new-create sprint73-data-maintenance-jobs`
