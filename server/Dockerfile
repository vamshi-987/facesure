FROM python:3.10-slim

# ---------- System dependencies ----------
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    cmake \
    libgl1 \
    libglib2.0-0 \
    patchelf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# ---------- FIX ONNXRUNTIME EXEC STACK ----------
RUN find /usr/local/lib/python3.10/site-packages/onnxruntime \
    -name "*.so" -exec patchelf --clear-execstack {} \;

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
