# trivy-service/Dockerfile

FROM python:3.11-slim
WORKDIR /app

# 1. Install prerequisites (wget, apt-transport-https, gnupg)
# Note: apt-transport-https and lsb-release are often unneeded now, but wget/gnupg are.
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Trivy (using a stable codename "bookworm" instead of "trixie")
# Fix is here: We replace "$(lsb_release -sc)" with "bookworm"
RUN wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | tee /usr/share/keyrings/trivy.gpg > /dev/null
RUN echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb bookworm main" | tee /etc/apt/sources.list.d/trivy.list

# 3. Final install and cleanup
# This step should now succeed
RUN apt-get update && apt-get install -y trivy \
    && rm -rf /var/lib/apt/lists/*
    
# 4. Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["python", "main.py"]