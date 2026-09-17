FROM python:3.11-slim

# opencv / easyocr / paddlepaddle runtime deps
# - libgl1, libglib2.0-0: opencv (paddleocr pulls in non-headless opencv-python
#   transitively, which needs these even though our own opencv pin is headless)
# - libgomp1: OpenMP runtime paddlepaddle needs (missing on -slim base images -
#   shows up as "libgomp.so.1: cannot open shared object file" at import time)
# - ffmpeg: video decoding for the detection pipeline
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    # paddleocr's install pulls in plain opencv-python as a transitive
    # dependency, which can silently shadow our pinned opencv-python-headless
    # in site-packages (both ship as the same `cv2` import). Reassert the
    # headless build last so it's what's actually loaded at runtime.
    && pip install --no-cache-dir --force-reinstall --no-deps opencv-python-headless==4.10.0.84

COPY . .

RUN mkdir -p data/uploads data/outputs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
