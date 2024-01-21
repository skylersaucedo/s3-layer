"""
use this to invoke FAST API to 
"""
import uvicorn
import boto3
from fastapi import FastAPI, File, UploadFile
import os

bucket = "tsi-mlops"
os.environ["DEFAULT_S3_BUCKET"] = bucket


app = FastAPI()
s3 = boto3.client('s3')

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    s3.upload_fileobj(file.file, bucket, file.filename)
    return {"message": "File uploaded successfully!"}

@app.get("/download")
async def download_file(file_name: str):
    with open(file_name, "wb") as f:
        s3.download_fileobj(bucket, file_name, f)
    return {"message": "File downloaded successfully!"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
    #app.run(debug=True, host='0.0.0.0', port=8080)