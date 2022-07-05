import datetime
from flask import Flask, render_template, request, redirect
from google.cloud import datastore
import google.oauth2.id_token
from google.auth.transport import requests
from google.cloud import storage
from requests import Response
import local_constants
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "testingcsp.json"
app = Flask(__name__)

# get access to the datastore client so we can add and store data in the datastore
datastore_client = datastore.Client()

# get access to a request adapter for firebase as we will need this to authenticate users
firebase_request_adapter = requests.Request()

def createUserInfo(claims):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore.Entity(key = entity_key)
    entity.update({
        'email': claims['email'],
        #'name': claims['name'],
    })
    datastore_client.put(entity)
    addDirectory(claims['email']+'/')

def retrieveUserInfo(claims):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore_client.get(entity_key)
    return entity

def blobList(prefix):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    return storage_client.list_blobs(local_constants.PROJECT_STORAGE_BUCKET,
prefix=prefix)

#create directory for user
def addDirectory(directory_name):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(directory_name)
    blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')

# add a image
def addSubFile(file, user):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(user+ file.filename)
    blob.upload_from_file(file)

#  add a folder or gallery
def addSubDirectory(directory_name,user):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(user+ directory_name)
    blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')

# delete image
def deleteBlobImage(filename):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(filename)
    blob.delete()

#get storage size
def getStorageSize(user):
    mystorage = 0
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob_list = blobList(user)
    for i in blob_list:
        blob = i.name
        blob = bucket.get_blob(blob)
        mystorage = mystorage + blob.size

    mystorage = mystorage/1000000
    mystorage = round(mystorage, 1)

    return mystorage

@app.route('/upload_file', methods=['post'])
def uploadFileHandler():
    id_token = request.cookies.get("token")
    claims = None
    mystorage = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
firebase_request_adapter)
            file = request.files['image']
            if file.filename == '':
                return redirect('/')
            user = claims['email']+'/'
            mystorage = getStorageSize(user)
            if mystorage <= 50:
                addSubFile(file, user)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')

@app.route('/add_directory', methods=['POST'])
def addDirectoryHandler():
    id_token = request.cookies.get("token")
    claims = None
    mystorage = 0
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
firebase_request_adapter)
            directory_name = request.form['dir_name']
            if directory_name == '' or directory_name[len(directory_name) - 1] != '/':
                return redirect('/')
            myuser = claims['email']+'/'
            mystorage = getStorageSize(myuser)
            if mystorage <= 50:
                addSubDirectory(directory_name, myuser)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')

@app.route('/delete_image/<string:filename>', methods=['POST'])
def deleteImage(filename):
    id_token = request.cookies.get("token")
    claims = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
firebase_request_adapter)
            myuser = claims['email']+ '/' + filename
            deleteBlobImage(myuser)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')

@app.route('/')
def root():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    myuser = None
    mystorage = 0 
    file_list = []
    directory_list = []
    mybucket = local_constants.PROJECT_STORAGE_BUCKET
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
            if user_info == None:
                createUserInfo(claims)
                user_info = retrieveUserInfo(claims)
            myuser = claims['email']+'/'
            mystorage = getStorageSize(myuser)
            blob_list = blobList(myuser)
            for i in blob_list:
                if i.name[len(i.name) - 1] == '/':
                    directory_list.append(i)
                else:
                    file_list.append(i)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('index.html', user_data=claims, error_message=error_message, mybucket =mybucket,
user_info=user_info, file_list=file_list, directory_list=directory_list, mystorage = mystorage, myuser = myuser)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
