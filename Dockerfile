FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libgdbm-dev \
    liblzma-dev \
    make \
    cmake \
    tzdata \
    && apt-get clean

RUN wget https://sourceforge.net/projects/ta-lib/files/ta-lib/0.4.0/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

#  Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && \
    rm /tmp/miniconda.sh

ENV PATH=/opt/conda/bin:$PATH

SHELL ["/bin/bash", "-c"]

RUN conda init bash && \
    conda create --name vectorbtpro python=3.11 -y && \
    echo "source /opt/conda/etc/profile.d/conda.sh && conda activate vectorbtpro" >> ~/.bashrc

# GitHub 
ARG GITHUB_USERNAME

RUN --mount=type=secret,id=github_token \
    GITHUB_TOKEN=$(cat /run/secrets/github_token) && \
    source /opt/conda/etc/profile.d/conda.sh && conda activate vectorbtpro && \
    pip install --upgrade pip wheel jupyter notebook plotly dash kaleido polygon-api-client && \
    pip install -U "vectorbtpro[base] @ git+https://${GITHUB_USERNAME}:${GITHUB_TOKEN}@github.com/polakowo/vectorbt.pro.git"

RUN --mount=type=secret,id=polygon_api_key \
    export API_KEY=$(cat /run/secrets/polygon_api_key) && \
    echo "export POLYGON_API_KEY=$API_KEY" >> ~/.bashrc

EXPOSE 8888

# Jupyter Server
CMD ["bash", "-i", "-c", \
     "source /opt/conda/etc/profile.d/conda.sh && \
     conda activate vectorbtpro && \
     jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root"]