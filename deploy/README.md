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


The workflow builds the image, starts a smoke-test container, pushes the image,
copies the compose file to the VM, writes `.env` on the VM from
`ENV_FILE_CONTENTS`, starts Postgres, runs the indexer for `tb,cervical_cancer`,
then starts the API.
