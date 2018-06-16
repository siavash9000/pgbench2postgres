FROM postgres:9.6
WORKDIR /workspace
ADD . /workspace
USER postgres
CMD python3 /workspace/benchmark.py