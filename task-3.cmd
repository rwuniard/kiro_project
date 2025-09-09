REM TASK 3: Implement Local Build Deployment Path
REM ============================================
REM 
REM STATUS: [ ] PENDING  [ ] IN PROGRESS  [ ] COMPLETED
REM 
REM OBJECTIVE: 
REM Create local deployment path that builds images locally using shared Dockerfile
REM and uses same environment generation and folder mapping as CI path.
REM 
REM ACTIONS:
REM 0. Ensure on refactor/build branch (created in Task 1)
REM    git checkout refactor/docker-deployment-reorganization
REM 
REM 1. Create docker_deployment/local/ directory
REM    mkdir docker_deployment/local
REM 
REM 2. Create docker_deployment/local/docker-compose.yml for local builds
REM    - Uses build context pointing to ../shared/Dockerfile
REM    - Same container config as CI path but builds instead of pulls
REM 
REM 3. Create docker_deployment/local/build-and-deploy.sh (Unix/Mac script)
REM    - Builds image locally using shared Dockerfile
REM    - Uses shared config and env generation (same as CI path)
REM    - Handles complex folder mapping (identical to CI path)
REM    - Sets up temp directory permissions
REM 
REM 4. Create docker_deployment/local/build-and-deploy.bat (Windows script)
REM    - Same functionality as .sh script but for Windows
REM    - Uses Windows-specific paths and commands
REM 
REM 5. Ensure build parity with CI
REM    - Verify local build produces same container as CI build
REM    - Same base image, same dependencies, same application code
REM    - Only difference: local vs GHCR storage
REM 
REM FILES TO CREATE:
REM - docker_deployment/local/docker-compose.yml (local build-based)
REM - docker_deployment/local/build-and-deploy.sh (Unix build+deploy script)
REM - docker_deployment/local/build-and-deploy.bat (Windows build+deploy script)
REM 
REM SHARED COMPONENTS USED:
REM - docker_deployment/shared/Dockerfile (for building)
REM - docker_deployment/shared/scripts/generate_env.py
REM - docker_deployment/shared/config/unix_paths.json
REM - docker_deployment/shared/config/windows_paths.json
REM - docker_deployment/shared/config/*_chroma_settings.json
REM 
REM VALIDATION:
REM - Local build completes successfully using shared Dockerfile
REM - Built image is identical to CI-built image (same layers)
REM - Complex folder mapping works correctly on both platforms
REM - Environment generation identical to CI path
REM - Temp directory permissions set correctly
REM - API key injection works from .env.local
REM - Container starts and health check passes
REM - No network dependency (works offline)
REM 
REM DEPENDENCIES: Task 1 (shared infrastructure)
REM BLOCKS: Task 5 (cleanup)
REM 
REM ESTIMATED TIME: 45 minutes
REM 
REM COMPLETION CHECKLIST:
REM [ ] local/ directory created
REM [ ] docker-compose.yml created for local builds
REM [ ] build-and-deploy.sh created and tested
REM [ ] build-and-deploy.bat created and tested
REM [ ] Scripts reference shared components correctly
REM [ ] Local build uses shared Dockerfile successfully
REM [ ] Build parity with CI verified (same image layers)
REM [ ] Environment generation identical to CI path
REM [ ] Folder mapping and permissions validated
REM [ ] Offline functionality confirmed
REM [ ] Changes committed to branch