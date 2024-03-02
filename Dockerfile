FROM public.ecr.aws/docker/library/python:3.11-bookworm

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

COPY requirements.txt /code/requirements.txt

RUN pip install --upgrade pip && \
   pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

WORKDIR /code/

RUN python -m app.preloader

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]