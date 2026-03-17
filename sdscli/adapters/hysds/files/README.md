# HySDS Jenkins Pipeline Configuration Files

This directory contains example configuration files for setting up Jenkins pipeline jobs with multi-architecture container build support.

## Files

### config-pipeline.xml
Generic Jenkins job configuration template for pipeline jobs. This file is used by `sds ci add_job --pipeline` to create Jenkins pipeline jobs.

**Template Variables:**
- `{{ PROJECT_URL }}` - Git repository URL
- `{{ BRANCH }}` - Git branch to build
- `{{ JENKINSFILE_PATH }}` - Path to Jenkinsfile in repository (default: `Jenkinsfile`)

**Usage:**
This file is automatically used when you run:
```bash
sds ci add_job <repo-url> <storage-type> --branch <branch> --pipeline
```

### Jenkinsfile.example
Example Jenkinsfile demonstrating multi-architecture container builds for HySDS projects.

**Features:**
- Multi-platform builds (amd64 + arm64)
- Single-architecture builds (amd64-only or arm64-only)
- Multi-platform manifest creation
- Metadata publishing to Mozart and GRQ
- Test artifact collection and reporting

**How to Use:**

1. **Copy to your project repository:**
   ```bash
   cp Jenkinsfile.example /path/to/your/project/Jenkinsfile
   ```

2. **Customize for your project:**
   - Add project-specific environment variables in the `environment` section
   - Customize build arguments in the build stages (search for `TODO` comments)
   - Add or remove build arguments as needed for your Dockerfile
   - Adjust artifact extraction if your project has different test outputs

3. **Common customizations:**
   
   **Add custom build arguments:**
   ```groovy
   --build-arg GIT_OAUTH_TOKEN=${GIT_OAUTH_TOKEN} \
   --build-arg BRANCH=${TAG} \
   --build-arg YOUR_CUSTOM_ARG=${YOUR_CUSTOM_VALUE} \
   ```
   
   **Add custom environment variables:**
   ```groovy
   environment {
       // ... existing vars ...
       CUSTOM_BRANCH = "${params.CUSTOM_BRANCH}"
       CUSTOM_CONFIG = "${params.CUSTOM_CONFIG}"
   }
   ```
   
   **Customize container-builder path:**
   The example uses generic paths. Update if your setup uses different paths:
   ```groovy
   ${OPS_HOME}/verdi/ops/container-builder/build-container.bash
   ```

4. **Commit to your repository:**
   ```bash
   git add Jenkinsfile
   git commit -m "Add Jenkins pipeline for multi-arch builds"
   git push
   ```

5. **Register with Jenkins:**
   ```bash
   sds ci add_job <your-repo-url> <storage-type> --branch <branch> --pipeline
   ```

## Build Modes

The example Jenkinsfile supports three build modes (controlled by Jenkins parameter):

- **`multi-platform`**: Builds both amd64 and arm64 in parallel, then creates a multi-platform manifest
- **`amd64-only`**: Builds only amd64 architecture
- **`arm64-only`**: Builds only arm64 architecture on ARM build nodes

## Jenkins Parameters

The following parameters should be configured in your Jenkins job:

**Required:**
- `BUILD_MODE` - Choice: multi-platform, amd64-only, arm64-only
- `GIT_OAUTH_TOKEN` - OAuth token for private repositories
- `MOZART_REST_URL` - Mozart REST API endpoint
- `GRQ_REST_URL` - GRQ REST API endpoint
- `STORAGE_URL` - S3/storage URL for artifacts
- `OPS_HOME` - HySDS ops home directory

**For multi-platform builds:**
- `CONTAINER_REGISTRY` - Container registry URL
- `CONTAINER_REGISTRY_BUCKET` - S3 bucket for registry storage
- `DOCKER_REGISTRY_TAR_FILE` - Docker registry tar file name
- `CONTAINER_BUILDER_REPO` - Container builder repository
- `CONTAINER_BUILDER_BRANCH` - Container builder branch
- `PUBLIC_GIT_OAUTH_TOKEN` - OAuth token for public repositories

## Notes

- ARM64 builds require Jenkins nodes with the `arm-build` label
- The example assumes container-builder is available in the verdi environment
- Customize the artifact extraction and test reporting sections based on your project's test framework
- The multi-platform manifest stage requires a container registry with S3 backend

## Additional Resources

- [HySDS Documentation](https://hysds.github.io/)
- [Jenkins Pipeline Syntax](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [Docker Buildx Multi-platform](https://docs.docker.com/build/building/multi-platform/)
