# Azure Functions Python custom container with Pandoc included
# Base image matches the runtime used by Azure Functions on Linux
FROM mcr.microsoft.com/azure-functions/python:4-python3.11-appservice

# Configure function host defaults
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Install Pandoc for EPUB conversion (keep image lean by cleaning apt artifacts)
RUN apt-get update \
    && apt-get install -y --no-install-recommends pandoc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pre-install dependencies for better layer caching
COPY requirements.txt /requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r /requirements.txt

# Copy the application code into the image
WORKDIR /home/site/wwwroot
COPY . /home/site/wwwroot
