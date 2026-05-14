
FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (already in the image, but just in case or for specific versions)
# The mcr image already has them, but we might need to ensure they are available
RUN playwright install chromium

# Copy application code
COPY . .

# Environment variables
ENV SCRAPE_INTERVAL=300
ENV STATION_URL="https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583"
ENV PROVIDER_NAME="Erlanger Stadtwerke"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
