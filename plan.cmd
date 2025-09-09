REM Docker Deployment Reorganization Plan
REM =========================================
REM 
REM OBJECTIVE: Reorganize deployment into two clear paths while maintaining build parity
REM 
REM CORE CHALLENGE: Build vs Deploy Separation
REM ---------------------------------------
REM Problem: CI build and local build must be identical, but deployment contexts 
REM          differ significantly in folder mapping complexity.
REM 
REM Solution: Separate build concerns from deployment concerns completely.
REM 
REM 
REM ARCHITECTURE STRATEGY
REM ====================
REM 
REM Build Layer (Identical for CI + Local)
REM -------------------------------------
REM - Single Dockerfile: Shared between CI and local builds
REM - Container-Internal Paths: Always /app/data/source, /app/data/saved, /app/data/error
REM - Environment-Agnostic: Container doesn't know about host paths
REM 
REM Deployment Layer (Context-Specific)
REM ---------------------------------
REM - Host Folder Mapping: Complex platform-specific logic via docker-compose volumes
REM - Environment Generation: Sophisticated .env creation for folder paths
REM - Runtime Configuration: API keys, model settings, monitoring config
REM 
REM 
REM FINAL STRUCTURE
REM ==============
REM 
REM docker_deployment/
REM ├── shared/                              # Common build infrastructure
REM │   ├── Dockerfile                       # Single source of truth for builds
REM │   ├── docker-compose.base.yml         # Common container configuration
REM │   ├── scripts/
REM │   │   └── generate_env.py             # Unified environment generation
REM │   └── config/
REM │       ├── unix_paths.json             # Unix/Mac folder configurations
REM │       ├── windows_paths.json          # Windows folder configurations
REM │       ├── dev_chroma_settings.json    # Development ChromaDB settings
REM │       └── prod_chroma_settings.json   # Production ChromaDB settings
REM ├── ci/                                 # Path A: Pull from GHCR
REM │   ├── docker-compose.yml              # Uses pre-built GHCR image
REM │   ├── deploy-from-ghcr.sh            # Unix: Pull + complex folder mapping
REM │   └── deploy-from-ghcr.bat           # Windows: Pull + complex folder mapping
REM └── local/                              # Path B: Local build
REM     ├── docker-compose.yml              # Builds from shared Dockerfile
REM     ├── build-and-deploy.sh            # Unix: Build + complex folder mapping
REM     └── build-and-deploy.bat           # Windows: Build + complex folder mapping
REM 
REM 
REM KEY DESIGN PRINCIPLES
REM ====================
REM 
REM 1. Build Parity
REM    - CI and local builds produce byte-identical containers
REM    - Same Dockerfile, same base image, same dependencies
REM    - Only difference: CI pushes to GHCR, local keeps locally
REM 
REM 2. Deployment Complexity Isolation
REM    - All sophisticated folder mapping logic shared between paths
REM    - Platform detection (Unix vs Windows) handled consistently
REM    - Temp directory permissions, API key management unified
REM 
REM 3. Path Independence
REM    - CI path works without local Docker build capability
REM    - Local path works without GHCR access or network connectivity
REM    - Each path has complete, standalone deployment scripts
REM 
REM 4. Maintainability
REM    - Single Dockerfile to maintain
REM    - Single .env generation logic
REM    - Platform-specific configs centralized in shared/config/
REM 
REM 
REM MIGRATION STRATEGY
REM =================
REM 
REM Current State:
REM - docker_deployment/ (mixed local build + CI logic) 
REM - docker_deployment_from_ghcr/ (GHCR pull deployment)
REM - GitHub Actions CI (builds and pushes to GHCR)
REM 
REM Migration Steps:
REM 1. Create shared infrastructure from existing docker_deployment/
REM 2. Create CI path from existing docker_deployment_from_ghcr/
REM 3. Create local path with shared components
REM 4. Consolidate and cleanup redundant files
REM 5. Update documentation and verify both paths work
REM 
REM 
REM EXPECTED BENEFITS
REM ================
REM ✓ Identical Builds: CI and local produce same containers
REM ✓ Deployment Flexibility: Choose quick GHCR pull vs local build control
REM ✓ Shared Complexity: Sophisticated folder mapping logic unified
REM ✓ CI Independence: Local deployment unaffected by CI changes
REM ✓ Clear Separation: Build concerns vs deployment concerns isolated
REM ✓ Better Maintenance: Single source of truth for common components
REM ✓ Platform Consistency: Same experience on Windows and Unix/Mac