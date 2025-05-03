FROM quay.io/fedora/python-313:313

USER 0

RUN yum -y update \
    && yum -y autoremove \
    && yum clean all \
    && rm -rf /var/cache/yum

WORKDIR /app

ADD src/scraper/ .

RUN chown -R 1001:0 ./

USER 1001

RUN pip install --upgrade pip && \
    pip install --upgrade -r ./requirements.txt

ENTRYPOINT [ "python", "main.py" ]

