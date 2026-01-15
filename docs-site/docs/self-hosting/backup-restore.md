---
sidebar_position: 5
---

# Backup & Restore

Protect your data with regular backups.

## Database Backup

### Docker Compose

```bash
# Backup
docker exec batchivo-postgres pg_dump -U batchivo batchivo > backup.sql

# With timestamp
docker exec batchivo-postgres pg_dump -U batchivo batchivo > backup-$(date +%Y%m%d).sql

# Compressed
docker exec batchivo-postgres pg_dump -U batchivo batchivo | gzip > backup-$(date +%Y%m%d).sql.gz
```

### Kubernetes

```bash
# Get postgres pod
kubectl get pods -n batchivo -l app=postgres

# Backup
kubectl exec -n batchivo postgres-0 -- pg_dump -U batchivo batchivo > backup.sql
```

### Direct PostgreSQL

```bash
pg_dump -h localhost -U batchivo batchivo > backup.sql
```

## Database Restore

### Docker Compose

```bash
# Restore
cat backup.sql | docker exec -i batchivo-postgres psql -U batchivo batchivo

# From compressed
gunzip -c backup.sql.gz | docker exec -i batchivo-postgres psql -U batchivo batchivo
```

### Kubernetes

```bash
cat backup.sql | kubectl exec -i -n batchivo postgres-0 -- psql -U batchivo batchivo
```

## Automated Backups

### Cron Job

Add to crontab (`crontab -e`):

```bash
# Daily backup at 2 AM
0 2 * * * docker exec batchivo-postgres pg_dump -U batchivo batchivo | gzip > /backups/batchivo-$(date +\%Y\%m\%d).sql.gz

# Weekly cleanup - keep 30 days
0 3 * * 0 find /backups -name "batchivo-*.sql.gz" -mtime +30 -delete
```

### Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: batchivo
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:16-alpine
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -h postgres -U batchivo batchivo | gzip > /backups/batchivo-$(date +%Y%m%d).sql.gz
            volumeMounts:
            - name: backups
              mountPath: /backups
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: password
          restartPolicy: OnFailure
          volumes:
          - name: backups
            persistentVolumeClaim:
              claimName: backup-pvc
```

## Backup Storage

### Local Storage

Store backups in a different location than your database:

```bash
# Create backup directory
mkdir -p /var/backups/batchivo

# Backup script
#!/bin/bash
BACKUP_DIR=/var/backups/batchivo
FILENAME=batchivo-$(date +%Y%m%d-%H%M%S).sql.gz

docker exec batchivo-postgres pg_dump -U batchivo batchivo | gzip > $BACKUP_DIR/$FILENAME

# Keep only last 30 backups
ls -t $BACKUP_DIR/*.sql.gz | tail -n +31 | xargs -r rm
```

### S3 Storage

```bash
# Backup to S3
docker exec batchivo-postgres pg_dump -U batchivo batchivo | gzip | \
  aws s3 cp - s3://my-bucket/backups/batchivo-$(date +%Y%m%d).sql.gz
```

## Testing Backups

Regularly test that backups can be restored:

```bash
# Create test database
createdb batchivo_test

# Restore backup
gunzip -c backup.sql.gz | psql -U batchivo batchivo_test

# Verify data
psql -U batchivo batchivo_test -c "SELECT COUNT(*) FROM spools;"

# Cleanup
dropdb batchivo_test
```

## Disaster Recovery

1. **Regular backups** - Daily minimum, hourly for critical data
2. **Off-site storage** - Store backups in different location/region
3. **Test restores** - Monthly restore tests
4. **Documentation** - Keep restore procedures documented
5. **Monitoring** - Alert on backup failures
