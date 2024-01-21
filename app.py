"""
use this to invoke FAST API to 
"""
import uvicorn
import boto3
from botocore.exceptions import NoCredentialsError
import requests
import mimetypes

from fastapi import FastAPI, File, UploadFile
import os

bucket = "tsi-mlops"
os.environ["DEFAULT_S3_BUCKET"] = bucket

ACCESS_KEY_ID = '***'
SECRET_ACCESS_KEY = '****'

app = FastAPI()

s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY_ID, aws_secret_access_key=SECRET_ACCESS_KEY)

@app.get("/")
def index():
    return {"message": "Hello S3 Layer for MLOps 21Jan2024"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:

        remote_url = 'https://github.com/skylersaucedo/s3-layer/blob/main/testimg.png'
        file_name = file.filename
        extension = file.content_type

        imageResponse = requests.get(remote_url, stream=True).raw
        print('img response: ', imageResponse)
        content_type = imageResponse.headers['content-type']
        extension = mimetypes.guess_extension(content_type)
        print('extension: ', extension)
        #extension = '.png'
        s3.upload_fileobj(imageResponse, bucket, file_name + extension)
        print("Upload Successful")
        return {"message": "File uploaded successfully!"}
    except FileNotFoundError:
        print("The file was not found")
        return {"message": "The file was not found"}
    except NoCredentialsError:
        print("Credentials not available")
        return {"message": "no creds!"}
    

@app.get("/download")
async def download_file(file_name: str):
    with open(file_name, "wb") as f:
        s3.download_fileobj(bucket, file_name, f)
    return {"message": "File downloaded successfully!"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
    #app.run(debug=True, host='0.0.0.0', port=8080)