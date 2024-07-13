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

# Create the Whisper model cache folder and download the models
RUN mkdir -p /root/.cache/whisper && \
    python -c "import whisper; whisper.load_model('medium')"

# Copy the rest of the application code
COPY README.md ./
COPY lyrics_transcriber ./lyrics_transcriber

# Install the lyrics-transcriber package
RUN poetry build && pip install dist/*.whl

# Set the entrypoint to run the CLI
ENTRYPOINT ["lyrics-transcriber"]

# Default command (can be overridden)
CMD ["--help"]