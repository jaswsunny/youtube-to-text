FROM python:3.12-slim

WORKDIR /app

# Install deno (yt-dlp's preferred JS runtime), ffmpeg, and yt-dlp
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    ffmpeg \
    && curl -fsSL https://deno.land/install.sh | sh \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir yt-dlp

ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py clean_podcast.py ./
COPY templates/ templates/
COPY static/ static/

# Expose port
EXPOSE 8080

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
