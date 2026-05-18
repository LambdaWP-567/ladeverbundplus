FROM mcr.microsoft.com/playwright:v1.43.0-jammy

WORKDIR /app

# Install Perl and build dependencies
RUN apt-get update && apt-get install -y \
    perl \
    libperl-dev \
    make \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install cpanminus
RUN curl -L https://cpanmin.us | perl - --self-upgrade

# Install perl dependencies
COPY cpanfile .
RUN cpanm --notest --installdeps .

# The Playwright perl module might need the node part
RUN npm install playwright@1.43.0

# Copy application code
COPY . .

# Persistence directory
RUN mkdir -p /app/data
VOLUME /app/data

# Environment variables
ENV SCRAPE_INTERVAL=300
ENV PROVIDER_NAME="Erlanger Stadtwerke"
ENV VERBOSE_LOGGING=false
ENV MOJO_MODE=production

EXPOSE 8000

CMD ["perl", "app.pl", "daemon", "-l", "http://0.0.0.0:8000"]
