FROM postgres:9.6
WORKDIR /workspace
ADD . /workspace
USER postgres
ENV PGDATABASE postgres
ENV PGPASSWORD postgres
ENV PGUSER postgres
CMD python3 /workspace/benchmark.py