# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy only the dependency files first
COPY pyproject.toml poetry.lock ./

# Install project dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Download the spacy model for english
RUN python -m spacy download en_core_web_sm

# Copy the rest of the application code
COPY README.md ./
COPY lyrics_transcriber ./lyrics_transcriber

# Install the lyrics-transcriber package
RUN poetry build && pip install dist/*.whl

# Set the entrypoint to run the CLI
ENTRYPOINT ["lyrics-transcriber"]

# Default command (can be overridden)
CMD ["--help"]