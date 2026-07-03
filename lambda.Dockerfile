# Python 3.12 usa Amazon Linux 2023 (GCC 11, glibc 2.34) en lugar de AL2 (GCC 7)
# Eso permite instalar wheels manylinux_2_28 de lightgbm, scipy, numpy 2.x sin compilar nada
FROM public.ecr.aws/lambda/python:3.12 AS builder

RUN dnf install -y libgomp gcc gcc-c++ make && dnf clean all

COPY requirements-lambda.txt .
RUN pip install --no-cache-dir -r requirements-lambda.txt --target /build/packages

# Stage 2 — runtime: sin compilador
FROM public.ecr.aws/lambda/python:3.12

RUN dnf install -y libgomp && dnf clean all

COPY --from=builder /build/packages /var/lang/lib/python3.12/site-packages/

COPY api/ api/
COPY ml/__init__.py ml/__init__.py
COPY ml/train_lgbm.py ml/train_lgbm.py
COPY etl/__init__.py etl/__init__.py
COPY etl/infra.py etl/infra.py

CMD ["api.lambda_handler.handler"]
