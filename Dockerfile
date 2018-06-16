FROM postgres:9.6
WORKDIR /workspace
ADD . /workspace
CMD python3 /workspace/benchmark.py