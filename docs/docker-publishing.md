# Docker Image Publishing

This document describes the GitHub Actions workflow for building and publishing multi-architecture Docker images for the Askaosus Matrix Bot.

## Overview

The project uses a GitHub Actions workflow (`.github/workflows/docker-publish.yml`) that automatically builds and publishes Docker images to the GitHub Container Registry (ghcr.io) for both AMD64 and ARM64 architectures.

## Architecture Support

- **AMD64 (x86_64)**: Built using standard GitHub-hosted runners (`ubuntu-latest`)
- **ARM64 (aarch64)**: Built using GitHub's native ARM64 runners (`ubuntu-24.04-arm64`)

## Tagging Strategy

The workflow uses different tagging strategies based on the trigger:

### Pull Request Builds (PR testing)
- Tests Docker builds on both architectures
- No images are published or pushed to the registry
- Validates that changes don't break the Docker build process
- Uses caching for faster builds

### Main Branch Builds (Push to `main`)
- `latest`: Latest stable build from the main branch
- `main`: Branch-specific tag

### Release Builds (Published releases)
- `v1.0`: Full semantic version tag (e.g., v1.2.3)
- `v1`: Major version tag (e.g., v1)
- `1.0`: Version without 'v' prefix (e.g., 1.2)

## Workflow Stages

The workflow behavior depends on the trigger:

### For Pull Requests (Testing Mode)
- **Environment Variable Testing**: Validates configuration loading without .env files
- **Docker Build Testing**: Builds both AMD64 and ARM64 images for validation
- **Configuration Validation**: Tests environment variable handling in containers
- No authentication or image pushing occurs
- Manifest creation is skipped
- Build caching is still utilized

### For Main Branch and Releases (Publishing Mode)

### 1. Build AMD64 (`build-amd64`)
- Runs on: `ubuntu-latest` 
- Platform: `linux/amd64`
- Pushes image with `-amd64` suffix

### 2. Build ARM64 (`build-arm64`)
- Runs on: `ubuntu-24.04-arm64` (native ARM runners)
- Platform: `linux/arm64` 
- Pushes image with `-arm64` suffix

### 3. Create Multi-Platform Manifest (`create-manifest`)
- Runs after both builds complete
- Creates unified manifest pointing to both architecture-specific images
- Publishes final multi-platform image tags

## Registry Details

- **Registry**: GitHub Container Registry (`ghcr.io`)
- **Image Name**: `ghcr.io/aosus/askaosus`
- **Authentication**: Uses `GITHUB_TOKEN` (automatically provided)

## Performance Features

- **Build Caching**: Uses GitHub Actions cache for faster builds
- **Parallel Builds**: AMD64 and ARM64 builds run in parallel
- **Layer Caching**: Docker layer caching enabled for both architectures

## Usage

### Pulling the Image

```bash
# Pull latest multi-platform image (recommended)
docker pull ghcr.io/aosus/askaosus:latest

# Pull specific version
docker pull ghcr.io/aosus/askaosus:v1.0

# Pull architecture-specific image (advanced usage)
docker pull ghcr.io/aosus/askaosus:latest-amd64
docker pull ghcr.io/aosus/askaosus:latest-arm64
```

### Docker Compose

The multi-platform image works seamlessly with the existing `docker-compose.yml`:

```yaml
services:
  askaosus-bot:
    image: ghcr.io/aosus/askaosus:latest
    environment:
      # Environment variables are passed directly - no .env file mounting needed
      - MATRIX_HOMESERVER_URL=${MATRIX_HOMESERVER_URL}
      - MATRIX_USER_ID=${MATRIX_USER_ID}
      - MATRIX_PASSWORD=${MATRIX_PASSWORD}
      # ... other variables
```

**Important**: The bot works entirely through environment variables. No `.env` file mounting is required or recommended for production deployments.

### Running with Environment Variables Only

```bash
# Run directly with Docker
docker run -d \
  --name askaosus-bot \
  -e MATRIX_HOMESERVER_URL=https://matrix.org \
  -e MATRIX_USER_ID=@askaosus:matrix.org \
  -e MATRIX_PASSWORD=your_password \
  -e DISCOURSE_API_KEY=your_api_key \
  -e DISCOURSE_USERNAME=your_username \
  -e LLM_API_KEY=your_llm_key \
  -v askaosus-data:/app/data \
  -v askaosus-logs:/app/logs \
  ghcr.io/aosus/askaosus:latest
```

## Triggers

The workflow triggers on:
- **Push to main branch**: Builds and publishes images, tags as `latest`
- **Pull requests**: Builds images for testing without publishing (validation only)
- **Published releases**: Builds and publishes images with version tags

## Requirements

For the workflow to function properly:

1. **Repository permissions**: The `GITHUB_TOKEN` needs `packages: write` permission
2. **ARM runner access**: Repository must have access to GitHub's ARM64 runners
3. **Container Registry**: GitHub Container Registry must be enabled for the repository

## Troubleshooting

### ARM64 Runner Unavailable
If ARM64 runners are not available, the workflow will fail at the `build-arm64` job. In such cases, consider:
1. Using QEMU emulation on standard runners
2. Building only AMD64 images temporarily
3. Contacting GitHub support for ARM runner access

### Registry Authentication
If image pushes fail, verify that:
1. Repository has Container Registry enabled
2. `GITHUB_TOKEN` has appropriate permissions
3. Repository visibility settings allow package publishing