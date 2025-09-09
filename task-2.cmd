REM TASK 2: Implement CI Deployment Path (GHCR Pull)
REM ==============================================
REM 
REM STATUS: [ ] PENDING  [ ] IN PROGRESS  [ ] COMPLETED
REM 
REM OBJECTIVE: 
REM Create CI deployment path that pulls pre-built images from GHCR and handles
REM complex folder mapping and environment configuration.
REM 
REM ACTIONS:
REM 0. Ensure on refactor/build branch (created in Task 1)
REM    git checkout refactor/docker-deployment-reorganization
REM 
REM 1. Create docker_deployment/ci/ directory
REM    mkdir docker_deployment/ci
REM 
REM 2. Create docker_deployment/ci/docker-compose.yml for GHCR images
REM    (Uses image: ${DOCKER_IMAGE} instead of build context)
REM 
REM 3. Create docker_deployment/ci/deploy-from-ghcr.sh (Unix/Mac script)
REM    - Pulls image from GHCR
REM    - Uses shared config and env generation
REM    - Handles complex folder mapping
REM    - Sets up temp directory permissions
REM 
REM 4. Create docker_deployment/ci/deploy-from-ghcr.bat (Windows script)
REM    - Same functionality as .sh script but for Windows
REM    - Uses Windows-specific paths and commands
REM 
REM 5. Update scripts to reference shared components
REM    - ../shared/scripts/generate_env.py
REM    - ../shared/config/unix_paths.json or windows_paths.json
REM    - ../shared/.env.template (if needed)
REM 
REM FILES TO CREATE:
REM - docker_deployment/ci/docker-compose.yml (GHCR image-based)
REM - docker_deployment/ci/deploy-from-ghcr.sh (Unix deployment script)
REM - docker_deployment/ci/deploy-from-ghcr.bat (Windows deployment script)
REM 
REM SHARED COMPONENTS USED:
REM - docker_deployment/shared/scripts/generate_env.py
REM - docker_deployment/shared/config/unix_paths.json
REM - docker_deployment/shared/config/windows_paths.json
REM - docker_deployment/shared/config/*_chroma_settings.json
REM 
REM VALIDATION:
REM - CI deployment scripts can pull latest image from GHCR
REM - Complex folder mapping works correctly on both platforms
REM - Environment generation works with shared components
REM - Temp directory permissions set correctly
REM - API key injection works from .env.local
REM - Container starts and health check passes
REM 
REM DEPENDENCIES: Task 1 (shared infrastructure)
REM BLOCKS: Task 4 (consolidation)
REM 
REM ESTIMATED TIME: 45 minutes
REM 
REM COMPLETION CHECKLIST:
REM [ ] ci/ directory created
REM [ ] docker-compose.yml created for GHCR images
REM [ ] deploy-from-ghcr.sh created and tested
REM [ ] deploy-from-ghcr.bat created and tested
REM [ ] Scripts reference shared components correctly
REM [ ] Environment generation works from shared location
REM [ ] GHCR image pull and deployment tested
REM [ ] Folder mapping and permissions validated
REM [ ] Changes committed to branch