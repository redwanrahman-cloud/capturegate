FROM public.ecr.aws/lambda/python:3.12
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt
COPY vision.py service.py rectify.py recovery.py page_crop.py public_guard.py judge_auth.py ${LAMBDA_TASK_ROOT}/
COPY web ${LAMBDA_TASK_ROOT}/web
CMD ["service.handler"]
