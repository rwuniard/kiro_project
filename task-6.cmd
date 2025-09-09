REM TASK 6: Testing and Validation
REM ==============================
REM 
REM STATUS: [ ] PENDING  [ ] IN PROGRESS  [ ] COMPLETED
REM 
REM OBJECTIVE: 
REM Thoroughly test both deployment paths on both platforms to ensure
REM reliability, build parity, and functionality equivalence.
REM 
REM ACTIONS:
REM 0. Ensure on refactor/build branch (created in Task 1)
REM    git checkout refactor/docker-deployment-reorganization
REM 
REM 1. Test CI Deployment Path (GHCR Pull)
REM    Unix/Mac:
REM    - cd docker_deployment/ci/
REM    - ./deploy-from-ghcr.sh [latest] [google]
REM    - Verify container starts and processes files correctly
REM    
REM    Windows:
REM    - cd docker_deployment\ci\
REM    - deploy-from-ghcr.bat latest google
REM    - Verify container starts and processes files correctly
REM 
REM 2. Test Local Build Deployment Path
REM    Unix/Mac:
REM    - cd docker_deployment/local/
REM    - ./build-and-deploy.sh [google]
REM    - Verify build completes and container starts correctly
REM    
REM    Windows:
REM    - cd docker_deployment\local\
REM    - build-and-deploy.bat google
REM    - Verify build completes and container starts correctly
REM 
REM 3. Verify Build Parity
REM    - Compare image layers between CI-built and locally-built images
REM    - docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.ID}}"
REM    - Verify identical functionality in both containers
REM    - Test same file processing with both deployments
REM 
REM 4. Test Platform-Specific Features
REM    Unix/Mac:
REM    - Verify /tmp/file-processor-unstructured permissions
REM    - Test with various file types (.docx, .pdf, .txt)
REM    - Verify folder mapping works correctly
REM    
REM    Windows:
REM    - Verify C:\temp\file-processor-unstructured creation
REM    - Test with various file types (.docx, .pdf, .txt)
REM    - Verify folder mapping works correctly
REM 
REM 5. Test Environment Generation
REM    - Test with both OpenAI and Google model vendors
REM    - Verify API key injection from .env.local
REM    - Test with missing .env.local (warning handling)
REM    - Verify ChromaDB path and collection settings
REM 
REM 6. Test Error Scenarios
REM    - Missing Docker/docker-compose
REM    - GHCR access denied (CI path)
REM    - Local build failures (Local path)
REM    - Missing configuration files
REM    - Invalid API keys
REM 
REM 7. Performance and Resource Testing
REM    - Verify memory limits work correctly (2G limit)
REM    - Test CPU limits work correctly (1.0 CPU limit)
REM    - Verify health checks function properly
REM    - Test log rotation (10m files, 3 max files)
REM 
REM TEST SCENARIOS:
REM - Fresh deployment on clean system
REM - Upgrade from old deployment scripts
REM - Multiple file types processing
REM - API key variations (OpenAI vs Google)
REM - Network availability variations
REM - Resource constraint scenarios
REM 
REM VALIDATION CRITERIA:
REM - Both paths deploy successfully on both platforms
REM - Identical image functionality between CI and local builds
REM - File processing works correctly in both deployments
REM - Environment generation produces valid configurations
REM - Error handling provides clear guidance
REM - Resource limits enforced correctly
REM - Health checks and logging function properly
REM - Documentation examples work as written
REM 
REM DEPENDENCIES: Task 1-5 (complete infrastructure and cleanup)
REM BLOCKS: Final merge and deployment
REM 
REM ESTIMATED TIME: 90 minutes
REM 
REM COMPLETION CHECKLIST:
REM [ ] CI deployment tested on Unix/Mac
REM [ ] CI deployment tested on Windows  
REM [ ] Local deployment tested on Unix/Mac
REM [ ] Local deployment tested on Windows
REM [ ] Build parity verified between CI and local
REM [ ] Platform-specific features validated
REM [ ] Environment generation tested (both vendors)
REM [ ] API key injection tested
REM [ ] Error scenarios tested
REM [ ] Resource limits validated
REM [ ] Health checks verified
REM [ ] Performance characteristics confirmed
REM [ ] Documentation examples verified
REM [ ] All tests passing
REM [ ] Final commit and branch ready for merge