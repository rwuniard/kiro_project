REM TASK 1: Create Shared Build Infrastructure
REM =========================================
REM 
REM STATUS: [ ] PENDING  [ ] IN PROGRESS  [ ] COMPLETED
REM 
REM OBJECTIVE: 
REM Create shared components that both CI and local deployment paths will use.
REM This ensures build parity and reduces duplication.
REM 
REM ACTIONS:
REM 0. Create refactor/build branch
REM    git checkout -b refactor/docker-deployment-reorganization
REM 
REM 1. Create docker_deployment/shared/ directory structure
REM    mkdir docker_deployment/shared
REM    mkdir docker_deployment/shared/scripts
REM    mkdir docker_deployment/shared/config
REM 
REM 2. Move Dockerfile from docker_deployment/ to docker_deployment/shared/
REM    mv docker_deployment/Dockerfile docker_deployment/shared/
REM 
REM 3. Move scripts/generate_env.py to docker_deployment/shared/scripts/
REM    mv docker_deployment/scripts/generate_env.py docker_deployment/shared/scripts/
REM 
REM 4. Move config/*.json files to docker_deployment/shared/config/
REM    mv docker_deployment/config/*.json docker_deployment/shared/config/
REM 
REM 5. Move .env.template to docker_deployment/shared/
REM    mv docker_deployment/.env.template docker_deployment/shared/
REM 
REM 6. Create docker_deployment/shared/docker-compose.base.yml with common container config
REM    (Create new file with base container configuration)
REM 
REM FILES TO CREATE/MOVE:
REM - docker_deployment/shared/Dockerfile (moved from docker_deployment/Dockerfile)
REM - docker_deployment/shared/scripts/generate_env.py (moved from docker_deployment/scripts/)
REM - docker_deployment/shared/config/unix_paths.json (moved from docker_deployment/config/)
REM - docker_deployment/shared/config/windows_paths.json (moved from docker_deployment/config/)
REM - docker_deployment/shared/config/dev_chroma_settings.json (moved from docker_deployment/config/)
REM - docker_deployment/shared/config/prod_chroma_settings.json (moved from docker_deployment/config/)
REM - docker_deployment/shared/.env.template (moved from docker_deployment/.env.template)
REM - docker_deployment/shared/docker-compose.base.yml (new file with common config)
REM 
REM VALIDATION:
REM - All files moved successfully to shared/ directory
REM - Original files removed from docker_deployment/ root
REM - generate_env.py still works from new location with relative path updates
REM - Dockerfile builds successfully from shared location
REM - Branch created and changes committed
REM 
REM DEPENDENCIES: None
REM BLOCKS: Task 2, Task 3
REM 
REM ESTIMATED TIME: 30 minutes
REM 
REM COMPLETION CHECKLIST:
REM [ ] Branch created
REM [ ] shared/ directory structure created
REM [ ] Dockerfile moved to shared/
REM [ ] generate_env.py moved and path references updated
REM [ ] All config JSON files moved to shared/config/
REM [ ] .env.template moved to shared/
REM [ ] docker-compose.base.yml created
REM [ ] All file movements validated
REM [ ] Changes committed to branch