# Kubernetes deployment path

Decision: ADR-021. Manifests: `infrastructure/kubernetes/` (kustomize). **Nothing in this
repository deploys to a cluster, and these manifests have not been applied to one** — they are
validated by rendering and by policy tests only. The supported target remains the local
Docker Compose demo (ADR-013); a public deployment additionally needs real authentication
(ADR-008).

## What is there

| Path | Contents |
|---|---|
| `base/` | Namespace (Pod Security `restricted`), ServiceAccount (no token), API Deployment + Service, web Deployment + Service, ingress-only NetworkPolicy, API ConfigMap |
| `jobs/migrate.yaml` | One-off `alembic upgrade head` Job, run before each API rollout |
| `overlays/example/` | Image tags and a TLS Ingress (`ingress-nginx` annotations: 12 MB body, SSE unbuffered) |

Not included, on purpose: PostgreSQL (use a managed instance), HPA and PodDisruptionBudget
(the API must be one replica — ADR-019), Helm (one environment shape).

## Validate locally

```bash
kubectl kustomize infrastructure/kubernetes/overlays/example
python -m pytest tests/infrastructure
```

The tests assert: hardened pods (non-root, read-only root FS, no privilege escalation, all
capabilities dropped, RuntimeDefault seccomp, no service-account token, requests and limits),
API `replicas: 1` + `Recreate` and no HPA, ClusterIP services only, no committed Secret objects,
probe paths that exist in the API, every configured variable read by `app.config.Settings`,
and a production-safe ConfigMap.

## Secrets

Create out of band; never commit:

```bash
kubectl -n arogyarakshak create secret generic arogyarakshak-api \
  --from-literal=DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/arogyarakshak' \
  --from-literal=DOCUMENT_SIGNING_SECRET="$(openssl rand -hex 32)" \
  --from-literal=CORS_ORIGINS='https://your-web-host' \
  --from-literal=GROQ_API_KEY='...'
```

Kubernetes Secrets are only base64-encoded in etcd. A real cluster needs etcd encryption at
rest (or an external secret store such as a cloud KMS-backed CSI driver), RBAC that limits
`get secrets` in the namespace, and a rotation procedure. The API refuses to start under
`APP_ENV=production` with a default or short signing secret, default DB credentials or a
wildcard CORS origin.

## Rollout order

1. Build and push both images; pin them by digest in your overlay.
2. Run the migration Job with the new API image tag and wait for completion.
3. `kubectl apply -k <your overlay>`. The API uses `Recreate`: expect a short gap (the
   startup probe allows up to 3 minutes for imports and model load).
4. Check `kubectl -n arogyarakshak get pods` and `/health/ready` through the ingress.

Rollback: re-apply the previous overlay (previous image digest). If the new revision added a
schema change, the previous code must still work against it — which is why migrations are
written backward-compatible (`database-migrations.md`).

## Resources

Requests/limits are **assumptions, not measurements**: API 500m/1.5 GiB requested, 2 CPU /
3 GiB limit (EasyOCR + torch load at first OCR); web 100m/256 MiB, 1 CPU/512 MiB. To size them,
run `scripts/evaluate_latency.py` and a representative scanned PDF against the container and
watch `docker stats` / `kubectl top pod`; raise the API memory limit if OCR is OOM-killed.
