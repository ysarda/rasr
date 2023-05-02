FROM python

WORKDIR /workspaces/rasr

RUN apt-get update && \
    apt-get install -y git

RUN useradd -ms /bin/bash docker
RUN mkdir -p /workspaces/rasr && chown -R docker:docker /workspaces/rasr
COPY --chown=docker:docker ./ /workspaces/rasr
USER docker

RUN pip install --upgrade pip
RUN pip install -r /workspaces/rasr/requirements.txt
RUN pip install -e /workspaces/rasr


