# NaviAble Production Deployment Notes

## TLS & Network Security

**Never deploy plain HTTP in production.** Run the backend behind a reverse proxy (nginx or Caddy) terminating TLS. Mobile apps (Android 9+ and iOS with ATS) reject plain HTTP by default.

Example nginx reverse proxy:
```nginx
server {
    listen 443 ssl http2;
    server_name api.naviable.example.com;
    
    ssl_certificate /etc/letsencrypt/live/api.naviable.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.naviable.example.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Static Asset Serving

### MVP: Local Disk
The `uploads/` directory is local-disk for MVP. Photos go to `backend/uploads/` and are served at `http://<backend>/static/<file>`.

### Production: S3 + CloudFront
For production, swap to S3 + CloudFront:

1. **Update `validate_and_persist_upload()` in `backend/app/services/image_persist.py`:**
   ```python
   import boto3
   
   s3_client = boto3.client('s3')
   s3_client.put_object(
       Bucket='naviable-uploads',
       Key=f'contributions/{uuid}.jpg',
       Body=image_bytes,
       ContentType='image/jpeg',
   )
   ```

2. **Update `_compose_image_url()` to return CDN URL:**
   ```python
   return f'https://cdn.naviable.example.com/contributions/{uuid}.jpg'
   ```

3. **Set environment variables:**
   ```bash
   AWS_ACCESS_KEY_ID=
   AWS_SECRET_ACCESS_KEY=
   AWS_S3_BUCKET=naviable-uploads
   AWS_CLOUDFRONT_DOMAIN=cdn.naviable.example.com
   ```

---

## Caching Strategy

### Maps SDK Cache
The TTL cache in `GooglePlacesService` is **per-process**. Behind a load balancer, deploy **one Redis instance** and cache there instead.

```python
# backend/app/services/google_places.py
import redis

cache = redis.Redis(host='redis-prod.internal', port=6379, db=0)

# Cache lookups for 3600 seconds
cache.setex(f'place:{place_id}', 3600, json.dumps(place_data))
```

Alternatively, just rely on the 60-second `Cache-Control` header we already set on API responses. Browsers and CDNs will respect it.

---

## CORS Configuration

Set `NAVIABLE_CORS_ORIGINS` to exact domains, **not `*`**. Mobile apps don't check CORS, but a future web client will.

```bash
# .env
NAVIABLE_CORS_ORIGINS=https://app.naviable.example.com,https://www.naviable.example.com
```

---

## Admin Endpoint Security

The training export endpoint (`/api/v1/training/export`) requires `X-Admin-Token`. In production, **bind it behind a separate `/admin` path that only internal IPs can reach.

```nginx
# nginx.conf
location /admin/ {
    # Restrict to internal IPs only
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    deny all;
    
    proxy_pass http://127.0.0.1:8000;
}
```

The `X-Admin-Token` is belt-and-braces, not a substitute for network-level isolation.

---

## Database Backup & Disaster Recovery

1. **Enable automated backups:**
   ```bash
   docker run -d --name naviable-backup \
     -v naviable_pgdata:/pgdata \
     -e BACKUP_PATH=/backups \
     -e BACKUP_INTERVAL=86400 \
     postgres:16 pg_dump -h naviable-postgis -U naviable naviable > /backups/daily.sql
   ```

2. **Test restore procedure monthly:**
   ```bash
   docker exec naviable-postgis psql -U naviable naviable < /backups/daily.sql
   ```

---

## Monitoring & Observability

### Logs
Stream backend logs to a centralized service (CloudWatch, Datadog, Splunk):
```python
# backend/app/main.py
import logging
logging.getLogger().addHandler(CloudWatchLogHandler(log_group='naviable-prod'))
```

### Metrics
Export Prometheus metrics from Uvicorn:
```python
# Installed via pip: prometheus-client
from prometheus_client import Counter, generate_latest

requests_total = Counter('requests_total', 'Total requests')
```

### Health Checks
The backend exposes `/healthz`. Use this for load balancer health checks:
```nginx
upstream backend {
    server backend-1:8000 max_fails=3 fail_timeout=30s;
    server backend-2:8000 max_fails=3 fail_timeout=30s;
}
```

---

## Environment Variables for Production

```bash
# .env (production)
POSTGRES_USER=naviable_prod
POSTGRES_PASSWORD=<strong-random-password>
DATABASE_URL=postgresql+psycopg://naviable_prod:<pwd>@postgres-prod.internal:5432/naviable

GOOGLE_PLACES_API_KEY=<prod-key>
ADMIN_TOKEN=<long-random-token>

UPLOAD_DIR=/mnt/naviable-uploads  # or S3 bucket
PUBLIC_BASE_URL=https://api.naviable.example.com
STATIC_PREFIX=/static/

NAVIABLE_CORS_ORIGINS=https://app.naviable.example.com
NAVIABLE_DEMO_MODE=false

# Scaling
WORKERS=8  # uvicorn: 2-4 per CPU core
```

---

## Load Balancing & Scaling

For high traffic:

1. **Horizontal scaling:**
   - Deploy 3+ backend instances behind a load balancer (nginx, HAProxy, AWS ALB)
   - Each instance runs its own Uvicorn worker pool (WORKERS=8)
   - Use read replicas for the database (PostgreSQL streaming replication)

2. **Database scaling:**
   - Enable connection pooling (pgBouncer, Prisma, or SQLAlchemy Pool)
   - Set `SQLALCHEMY_POOL_SIZE=20` and `SQLALCHEMY_POOL_RECYCLE=3600`

3. **CDN for static assets:**
   - Serve all images through CloudFront/Cloudflare (see S3 section above)
   - Cache CSS/JS bundles for 1 week

---

## Security Checklist

- [ ] TLS termination enabled (HTTPS only)
- [ ] Admin endpoints behind network ACLs
- [ ] Database password rotated (not default `naviable_dev`)
- [ ] `GOOGLE_PLACES_API_KEY` restricted by IP (backend servers only)
- [ ] `ADMIN_TOKEN` is a long random string
- [ ] `NAVIABLE_CORS_ORIGINS` is set (not `*`)
- [ ] Backups tested monthly
- [ ] Logs centralized and monitored
- [ ] Rate limiting enabled (API Gateway or nginx)
- [ ] DDoS protection enabled (Cloudflare, AWS Shield)

---

## Disaster Recovery Time Estimates

| Scenario | Recovery Time | Mitigation |
|----------|---------------|-----------|
| Single backend instance fails | <30s | Load balancer redirects to healthy instance |
| Database replica falls behind | <5m | Automated sync or manual `pg_rewind` |
| Data corruption in uploads bucket | <1h | Restore from S3 versioning + CloudFront cache invalidate |
| Sustained 100x traffic spike | <10m | Auto-scaling group increases instance count |
| Region-wide outage | >1h | Failover to backup region (multi-region setup) |

---

## Rollback Procedure

If a new backend version introduces a critical bug:

```bash
# 1. Check the current running version
curl https://api.naviable.example.com/health | jq .version

# 2. Get the previous stable version
git log --oneline | head -10

# 3. Roll back
docker pull naviable-backend:v1.2.3
docker stop naviable-backend
docker run -d --name naviable-backend naviable-backend:v1.2.3

# 4. Verify health
curl https://api.naviable.example.com/health
```

Always test rollback in staging first.
