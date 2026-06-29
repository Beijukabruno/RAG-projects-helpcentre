# Helpcentre Deployment

This deployment runs the multi-project Helpcentre API for the projects configured in
`config/projects.yaml`, currently `tb` and `cervical_cancer`.

## Image and services

The Docker image is named generically:

- `DOCKERHUB_USERNAME/helpcentre-api:latest`
- `DOCKERHUB_USERNAME/helpcentre-api:<git-sha>`

The compose services are:

- `helpcentre_postgres`: PostgreSQL with pgvector
- `helpcentre_indexer`: one-shot chunking and indexing job
- `helpcentre_api`: FastAPI service

## Local run

Create `.env` from `.env.example`, then run:

```bash
docker compose -f deploy/docker/docker-compose.local.yml up -d helpcentre_postgres
docker compose -f deploy/docker/docker-compose.local.yml run --rm helpcentre_indexer
docker compose -f deploy/docker/docker-compose.local.yml up -d helpcentre_api
```

The local API defaults to:

```text
http://localhost:8000/health
http://localhost:8000/ready
```

## Production deployment

The GitHub Actions workflow `.github/workflows/deploy_to_vm.yml` runs on pushes to
`main` and can also be started manually.

Required GitHub secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_ACCESS_TOKEN`
- `VM_HOST`
- `VM_USER`
- `VM_SSH_KEY`
- `VM_APP_PATH`
- `ENV_FILE_CONTENTS`

`ENV_FILE_CONTENTS` should contain the production environment variables. Use
`deploy/env.production.example.txt` as the template. The workflow appends
`HELPCENTRE_IMAGE` automatically for the exact image tag it just built.


The workflow builds and pushes the image, copies the compose file to the VM,
writes `.env` on the VM from `ENV_FILE_CONTENTS`, starts Postgres if it is not
already running, starts the API with the new image, then confirms the deployed
service responds on `/health` before completing.

Knowledge-base indexing is intentionally separate from the normal deployment
path. On a manual workflow run, set `run_indexer=true` to run the one-shot
indexer after the API is already deployed and healthy. Use `index_projects` to
limit the job to a subset such as `tb`, and use `force_rechunk=true` only when
the markdown sources changed and chunk JSON files must be rebuilt.

By default, the indexer uses existing generated chunk files in the image and
only creates missing chunk files. This avoids semantic chunking API calls during
routine deploys. The embedding step runs with resume enabled, skipping
unchanged chunks and reusing existing embeddings when identical chunk text is
seen under a new chunk id.

For large knowledge bases, prefer `chunking_strategy=recursive` when forcing a
rechunk. Semantic chunking calls the embedding model during splitting, so it is
slower and should be reserved for deliberate rebuilds where the quality tradeoff
is worth the extra API time. The manual workflow also exposes `index_batch_size`
to tune embedding batch size without changing the image.
