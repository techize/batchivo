# PRD: MinIO/S3 Object Storage for Product Images

## Problem Statement

Nozzly currently stores product images on the local filesystem of backend pods. With multiple replicas running, uploads go to random pods, causing:
- **Split-brain uploads**: Files exist on one pod but not others
- **Broken images**: Requests may hit pods that don't have the file
- **No persistence**: Pod restarts lose all uploaded images
- **No backup strategy**: Images are not backed up

## Goals

1. **Shared storage**: All backend pods access the same image storage
2. **Persistence**: Images survive pod restarts and deployments
3. **Backup strategy**: Automated backups to prevent data loss
4. **AWS-ready**: Architecture that easily migrates to AWS S3 later
5. **Zero downtime**: Migrate existing images without service interruption

## Solution: MinIO on Kubernetes

Deploy MinIO as an S3-compatible object storage service within the k3s cluster.

### Architecture

```
Backend Pods (2+)  ──S3 API──►  MinIO Service  ──►  MinIO Pod
                                     │
                                     ▼
                               PVC (10Gi+)
                                     │
                                     ▼
                            NFS Backup (nightly)
```

## Technical Requirements

### Phase 1: MinIO Deployment

#### 1.1 Kubernetes Resources
- **Namespace**: Use existing `nozzly` namespace
- **Deployment**: Single MinIO pod (can scale later)
- **Service**: ClusterIP for internal access
- **PVC**: 10Gi persistent volume for data
- **Secret**: MinIO root credentials (access key, secret key)
- **ConfigMap**: MinIO configuration

#### 1.2 MinIO Configuration
- **Port**: 9000 (API), 9001 (Console)
- **Bucket**: `nozzly-images` (auto-created on startup)
- **Access**: Internal only (no public ingress for now)
- **Console**: Optional ingress for admin access

### Phase 2: Backend Integration

#### 2.1 Update ImageStorage Service
The backend already has `_save_s3` method stubbed. Implement:
- S3 client initialization (boto3 or aioboto3)
- Upload with automatic content-type detection
- Generate presigned URLs or proxy through backend
- Delete objects when images are removed
- Rotate images (download, rotate, re-upload)

#### 2.2 Configuration
Add to backend settings:
```python
STORAGE_TYPE: str = "s3"  # or "local"
S3_ENDPOINT_URL: str = "http://minio:9000"
S3_ACCESS_KEY: str
S3_SECRET_KEY: str
S3_BUCKET_NAME: str = "nozzly-images"
S3_REGION: str = "us-east-1"  # Required by boto3
S3_PUBLIC_URL: str = ""  # For presigned URLs or CDN
```

#### 2.3 Image URL Strategy
Two options:
1. **Presigned URLs**: Generate time-limited signed URLs (more secure)
2. **Backend proxy**: Serve images through `/api/v1/images/{path}` (simpler)

Recommendation: Start with backend proxy, add presigned URLs later.

### Phase 3: Migration

#### 3.1 Migrate Existing Images
- Script to copy files from pod local storage to MinIO
- Update database records if URL format changes
- Verify all images accessible after migration

#### 3.2 Cleanup
- Remove local storage directories from pods
- Update deployment to remove local volume mounts

### Phase 4: Backup Strategy

#### 4.1 MinIO to NFS Backup
- CronJob: Nightly `mc mirror` from MinIO to NFS share
- Retention: Keep 7 daily backups
- Location: `/mnt/nfs/backups/nozzly-images/`

#### 4.2 Monitoring
- Alert if backup job fails
- Monitor MinIO disk usage
- Alert at 80% capacity

## Future: AWS S3 Migration

When ready to migrate to AWS S3:
1. Change `S3_ENDPOINT_URL` to AWS S3 endpoint
2. Update credentials to AWS IAM
3. Use `mc mirror` to sync MinIO → S3
4. Update `S3_PUBLIC_URL` for CloudFront CDN
5. Decommission MinIO

## Non-Goals (Out of Scope)

- Multi-region replication
- Image CDN/caching (future enhancement)
- Image transformation service (resize on-the-fly)
- Public bucket access (all through backend)

## Success Criteria

1. All backend pods can read/write images to same storage
2. Images persist across pod restarts
3. Nightly backups running successfully
4. Existing images migrated with zero broken links
5. No user-facing downtime during migration

## Dependencies

- NFS server for backups (existing: `nfsserver` at 192.168.2.14)
- PVC provisioner (existing: local-path)

## Timeline

- Phase 1 (MinIO Deploy): 1-2 hours
- Phase 2 (Backend Integration): 2-3 hours
- Phase 3 (Migration): 1 hour
- Phase 4 (Backup): 1 hour

Total: ~6 hours of implementation work

## Risks

| Risk | Mitigation |
|------|------------|
| MinIO pod failure | PVC persists data; pod restarts automatically |
| Data loss | Nightly backups to NFS |
| Performance | MinIO is fast; monitor latency |
| Complexity | S3 API is standard; boto3 well-documented |

## References

- [MinIO Kubernetes Deployment](https://min.io/docs/minio/kubernetes/upstream/)
- [boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- Current ImageStorage: `backend/app/services/image_storage.py`
