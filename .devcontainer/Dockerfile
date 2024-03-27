FROM mcr.microsoft.com/devcontainers/miniconda:0-3 AS base

ARG UNAME=vscode
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG PYPI_USER
ARG PYPI_PASS

USER root
RUN groupmod -g $GROUP_ID $UNAME
RUN usermod -u $USER_ID -g $GROUP_ID $UNAME

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends poppler-utils ffmpeg libsm6 libxext6

USER $UNAME
WORKDIR /home/$UNAME

ENV PATH=/home/$UNAME/.local/bin:$PATH
ENV PIP_EXTRA_INDEX_URL=https://$PYPI_USER:$PYPI_PASS@pypiserver.paipaya.com/

# USE PYTHON 3.10 BECAUSE OF FASTDEPLOY IS NOT SUPPORTED IN 3.11 YET
COPY conda.yaml conda-ai.yaml
RUN /opt/conda/bin/conda env create -n aibutlerhat -f conda-ai.yaml

# Install web_env conda env
COPY web/conda.yml conda-web.yaml
RUN /opt/conda/bin/conda env create -n web_env -f conda-web.yaml

WORKDIR /workspaces/ai-butlerhat

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