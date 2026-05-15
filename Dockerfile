FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Copy application code
COPY . .

# Persistence directory
RUN mkdir -p /app/data
VOLUME /app/data

# Environment variables
ENV SCRAPE_INTERVAL=300
ENV PROVIDER_NAME="Erlanger Stadtwerke"
ENV VERBOSE_LOGGING=false

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
