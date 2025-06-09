FROM python:3.13-slim

# Install system dependencies including Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    gcc \
    postgresql-client \
    # Chromium dependencies
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy Poetry files
COPY pyproject.toml ./

# Install dependencies (generate lock file if needed)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Install Playwright browsers
RUN playwright install chromium

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "src.cli", "--help"]