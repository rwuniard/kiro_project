FROM python:3.12-slim

# Copy the env file
COPY docker_deployment/.env* ./

# List and show the env files
RUN ls -la .env*
RUN echo "=== Content of .env ==="
RUN cat .env || echo "No .env file found"
RUN echo "=== Content of .env.generated ==="
RUN cat .env.generated || echo "No .env.generated file found"

# Test loading with Python
RUN echo "=== Python dotenv test ===" && python3 -c "import os; print('MODEL_VENDOR check:'); [print(line.strip()) for line in open('.env') if 'MODEL_VENDOR' in line]"

CMD ["echo", "Test complete"]