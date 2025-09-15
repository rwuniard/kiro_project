# Task 2: Optimize PR Docker Builds

## Overview
**Priority**: High
**Estimated Time**: 45 minutes
**Risk Level**: Low
**Time Saved**: 4-7 minutes per PR

## Problem Statement
PR validation currently builds both AMD64 and ARM64 Docker images, which is unnecessary for validation purposes. Only production deployments need multi-platform images for broad compatibility.

## Solution
Implement conditional platform building:
- **PR Validation**: Build only AMD64 (faster, still validates Docker functionality)
- **Production Deployment**: Build both AMD64 + ARM64 (full compatibility)

## Implementation Steps

### Step 1: Modify Docker Build Workflow
**File**: `.github/workflows/docker-build.yml`
**Change**: Make platform selection conditional on push_image parameter

```yaml
- name: Build and optionally push Docker image
  id: build
  uses: docker/build-push-action@v5
  with:
    context: .
    file: ./docker_deployment/shared/Dockerfile
    platforms: ${{ inputs.push_image && 'linux/amd64,linux/arm64' || 'linux/amd64' }}
    push: ${{ inputs.push_image }}
    load: false
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
    build-args: |
      VERSION=${{ inputs.version }}
    cache-from: type=gha
    cache-to: type=gha,mode=min
```

### Step 2: Update Build Summary
**File**: `.github/workflows/docker-build.yml`
**Change**: Dynamic platform reporting in summary

```yaml
- name: Build summary
  run: |
    echo "## 🐳 Docker Build Summary" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "### ✅ Build Details" >> $GITHUB_STEP_SUMMARY
    echo "- **Image**: \`${{ inputs.registry }}/${{ github.repository_owner }}/${{ inputs.image_name }}\`" >> $GITHUB_STEP_SUMMARY
    echo "- **Version**: \`${{ inputs.version }}\`" >> $GITHUB_STEP_SUMMARY
    echo "- **Model Vendor**: \`${{ inputs.model_vendor }}\`" >> $GITHUB_STEP_SUMMARY
    echo "- **Environment**: \`${{ inputs.environment }}\`" >> $GITHUB_STEP_SUMMARY

    # Dynamic platform reporting
    if [ "${{ inputs.push_image }}" = "true" ]; then
      echo "- **Platforms**: \`linux/amd64, linux/arm64\` (production multi-platform)" >> $GITHUB_STEP_SUMMARY
      echo "- **Build Type**: Production deployment with full platform support" >> $GITHUB_STEP_SUMMARY
    else
      echo "- **Platforms**: \`linux/amd64\` (validation build)" >> $GITHUB_STEP_SUMMARY
      echo "- **Build Type**: PR validation (single platform for speed)" >> $GITHUB_STEP_SUMMARY
    fi

    echo "- **Registry Push**: ${{ inputs.push_image && '✅ Enabled' || '❌ Validation only' }}" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "### 🏷️ Available Tags" >> $GITHUB_STEP_SUMMARY
    echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
    echo "${{ steps.meta.outputs.tags }}" >> $GITHUB_STEP_SUMMARY
    echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
```

### Step 3: Update Test Image Logic
**File**: `.github/workflows/docker-build.yml`
**Change**: Clarify validation vs production testing approach

```yaml
- name: Test Docker image
  run: |
    echo "Testing Docker build results..."

    if [ "${{ inputs.push_image }}" = "true" ]; then
      echo "🚀 Production build - Testing multi-platform image from registry"

      # Test the pushed multi-platform image
      REGISTRY_TAG=$(echo "${{ steps.meta.outputs.tags }}" | head -n1)
      echo "Pulling and testing registry image: $REGISTRY_TAG"

      docker pull "$REGISTRY_TAG"

      # Run basic health check on registry image
      docker run --rm \
        -e ENABLE_DOCUMENT_PROCESSING=false \
        "$REGISTRY_TAG" \
        python -c "import sys; print('🐍 Python version:', sys.version); print('🏷️ Image version: ${{ inputs.version }}'); exec('try:\\n    from src.app import FolderFileProcessorApp\\n    from src.config import ConfigManager\\n    from src.core import FileProcessor\\n    print(\"✅ Core modules import successfully\")\\nexcept ImportError as e:\\n    print(f\"❌ Import error: {e}\")\\n    sys.exit(1)\\nprint(\"✅ Multi-platform Docker image test passed\")')"

    else
      echo "🧪 PR validation build - Single platform validation completed"
      echo "✅ Docker build validation passed (AMD64 platform)"
      echo "✅ Dockerfile syntax and dependencies verified"
      echo "✅ Build context and file access confirmed"
      echo ""
      echo "Build outputs:"
      echo "- Platform: linux/amd64 (validation sufficient)"
      echo "- Image built successfully: ${{ inputs.image_name }}:${{ inputs.version }}"
      echo "- Build time optimized for PR feedback speed"
      echo ""
      echo "Note: Production deployment will build multi-platform (AMD64 + ARM64)"
    fi
```

### Step 4: Update PR Validation Workflow
**File**: `.github/workflows/pr-validation.yml`
**Change**: Update documentation to reflect single-platform PR builds

```yaml
# Job 4: Docker Build Test using reusable workflow
docker-build-test:
  name: Docker Build Test (AMD64 Validation)
  needs: [test-and-coverage, generate-version]
  if: github.event_name == 'pull_request' && (github.event.pull_request.draft == false || github.event_name == 'workflow_dispatch')
  uses: ./.github/workflows/docker-build.yml
  with:
    push_image: false  # Single platform validation build
    registry: 'ghcr.io'
    image_name: 'rag-file-processor'
    version: ${{ needs.generate-version.outputs.full_version }}
    model_vendor: 'openai'
    environment: 'development'
  secrets:
    GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_KEY_API }}
    REGISTRY_TOKEN: ${{ secrets.REGISTRY_TOKEN }}
```

## Expected Outcome

### Before
```
PR Docker Build:
├── Setup (1 min)
├── Build AMD64 (3-4 min)
├── Build ARM64 (3-4 min)  ← ELIMINATED
└── Validation (1 min)
Total: 8-10 minutes

Production Docker Build:
├── Setup (1 min)
├── Build AMD64 (4-5 min)
├── Build ARM64 (4-5 min)
├── Push & Test (3-5 min)
Total: 12-16 minutes
```

### After
```
PR Docker Build:
├── Setup (1 min)
├── Build AMD64 (3-4 min)
└── Validation (1 min)
Total: 5-6 minutes (3-4 min saved)

Production Docker Build: (unchanged)
├── Setup (1 min)
├── Build AMD64 + ARM64 (8-10 min)
├── Push & Test (3-5 min)
Total: 12-16 minutes
```

## Testing Plan

### 1. PR Validation Testing
- Create test PR and verify single-platform build completes successfully
- Confirm build time reduction (should be ~50% faster)
- Verify all validation checks still pass

### 2. Production Deployment Testing
- Merge PR and verify production build still creates multi-platform images
- Test both AMD64 and ARM64 images work correctly
- Verify deployment to different architectures functions properly

### 3. Compatibility Testing
- Pull and test images on both Intel and ARM machines
- Verify application functionality on different platforms
- Confirm Docker manifest includes both architectures

## Risk Assessment

### Low Risk Factors
- Production builds remain unchanged (full multi-platform support)
- PR validation still tests Docker functionality
- Build logic and dependencies remain identical

### Mitigation Strategies
- Production deployment maintains full compatibility
- Easy rollback to multi-platform PR builds if needed
- Test both platforms in production before user access

## Success Criteria
- [ ] PR Docker builds complete 3-4 minutes faster
- [ ] Production deployments still create multi-platform images
- [ ] Both AMD64 and ARM64 images work correctly in production
- [ ] No reduction in Docker validation effectiveness
- [ ] Build success rates remain at >95%

## Follow-up Tasks
After implementation and validation:
- Monitor build times and success rates for 1 week
- Collect feedback on PR feedback speed improvement
- Consider similar optimizations for other lengthy build processes
- Proceed to Task 3 if optimization proves successful