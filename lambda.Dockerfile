FROM public.ecr.aws/lambda/python:3.11

# LightGBM depende de libgomp (OpenMP) para paralelismo interno
RUN yum install -y libgomp && yum clean all

COPY requirements-lambda.txt .
RUN pip install --no-cache-dir -r requirements-lambda.txt

# Solo lo necesario para inferencia — sin ETL, sin training, sin PyTorch
COPY api/ api/
COPY ml/__init__.py ml/__init__.py
COPY ml/train_lgbm.py ml/train_lgbm.py
COPY etl/__init__.py etl/__init__.py
COPY etl/infra.py etl/infra.py

CMD ["api.lambda_handler.handler"]
