# FaceAuth System

ML-powered Face Authentication system using FastAPI, InsightFace, ONNXRuntime.

## Requirements
- Docker Desktop

## Run locally

```bash
git clone https://github.com/<your-username>/faceauth-system.git
cd faceauth-system
docker build -t faceauth-system .
docker run -p 5000:5000 faceauth-system
