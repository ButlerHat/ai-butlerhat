FROM mcr.microsoft.com/devcontainers/miniconda:0-3 AS base

ARG UNAME=vscode
ARG USER_ID=1000
ARG GROUP_ID=1000

USER root
RUN groupmod -g $GROUP_ID $UNAME
RUN usermod -u $USER_ID -g $GROUP_ID $UNAME

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends poppler-utils ffmpeg libsm6 libxext6

# USE PYTHON 3.10 BECAUSE OF FASTDEPLOY IS NOT SUPPORTED IN 3.11 YET
COPY conda.yaml* .devcontainer/noop.txt /tmp/conda-tmp/
# RUN /opt/conda/bin/conda update -n base -c defaults conda
RUN if [ -f "/tmp/conda-tmp/conda.yaml" ]; then umask 0002 && /opt/conda/bin/conda env update -n base -f /tmp/conda-tmp/conda.yaml; fi
RUN rm -rf /tmp/pip-tmp

USER $UNAME

ENV HF_HOME="/workspaces/ai-butlerhat/.hf_cache"
ENV HF_DATASETS_CACHE="/workspaces/ai-butlerhat/.hf_cache"


FROM base AS prod 

ARG GITHUB_TOKEN
ARG WANDB_API_KEY
ARG WANDB_MODEL

USER root
RUN wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && dpkg -i cloudflared-linux-amd64.deb

COPY . /workspaces/ai-butlerhat
WORKDIR /workspaces/ai-butlerhat
RUN mkdir -p /workspaces/ai-butlerhat/model && chown -R $UNAME:$UNAME /workspaces/ai-butlerhat

# Install conda env for prod. Installing with root user seems to be fine because install in /opt/conda
WORKDIR /workspaces/ai-butlerhat/.devcontainer/prod
RUN python resolve_conda_secret.py --token $GITHUB_TOKEN
RUN conda env update -n base -f conda_pass.yaml

USER $UNAME
# Download model
ENV WANDB_API_KEY=$WANDB_API_KEY
RUN wandb artifact get $WANDB_MODEL --root /workspaces/ai-butlerhat/model/

WORKDIR /workspaces/ai-butlerhat
CMD ["bash", "./.devcontainer/prod/postCreateCommand.sh"]