
FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The base image already contains the browsers in /ms-playwright
# We don't need to RUN playwright install chromium here if we use the right image.
# However, to be absolutely sure and avoid a 500MB download during runtime,
# we keep it but it should ideally be part of the base.
# To optimize, we can check if it's already there.
RUN playwright install chromium

# Copy application code
COPY . .

# Environment variables
ENV SCRAPE_INTERVAL=300
ENV STATION_URL="https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583"
ENV PROVIDER_NAME="Erlanger Stadtwerke"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
