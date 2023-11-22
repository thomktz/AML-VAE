import httplib2
import socket
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
import os.path

httplib2.Http(timeout=360)  # Set a higher timeout, e.g., 360 seconds


# Define the scopes and the credentials file
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'drive_key.json'

def authenticate_gdrive():
    creds = None
    # Load existing credentials if they exist
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            flow.run_local_server(port=0)
            creds = flow.credentials

            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def upload_file(file_name, file_path, creds):
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, mimetype='video/mp4')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"File ID: {file.get('id')}")

# Authenticate and upload a file
creds = authenticate_gdrive()
upload_file('compressed_video.mp4', 'compressed_video.mp4', creds)
