FROM public.ecr.aws/docker/library/python:3.11-bookworm

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

# Install uv for faster pip installs. See https://github.com/astral-sh/uv
RUN pip install uv

COPY requirements.txt /code/requirements.txt

RUN uv pip install --system -r /code/requirements.txt \
   uv cache clean

COPY ./app /code/app

WORKDIR /code/

RUN python -m app.preloader

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]