# Import Python Libraries
import glob
import azure.cognitiveservices.speech as speechsdk
import time
import json
import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

def transcribe():
    #get the cognitive services key and region from the config file
    speech_key = os.environ.get("speech_key")
    service_region = os.environ.get("service_region")

    #get the blob storage details where the audio file is stored and where the converted text file has to be uploaded
    blob_connection_string = os.environ.get("blob_connection_string")
    blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
    input_container_name = "audiofiles"
    output_container_name = "output-text"
    input_audio_filename = "Diabetes interview 1.wav"
    output_blob_filename = input_audio_filename + r"-converted.txt" 
    blob_container_client = blob_service_client.get_container_client(container=input_container_name)
    blob_client = blob_service_client.get_blob_client(container=input_container_name, blob=input_audio_filename)
    #blob_list = blob_container_client.list_blobs()   
    with open(input_audio_filename, "wb") as f:
        data = blob_client.download_blob()
        data.readinto(f)   

    #print("speech_key: " + speech_key)
    print("service_region: " + service_region)

    # Creates an instance of a speech config with specified subscription key and service region.
    speech_key, service_region = speech_key, service_region
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    
    def speech_recognize_continuous_from_file(file):
        """performs continuous speech recognition with input from an audio file"""
        # <SpeechContinuousRecognitionWithFile>
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        audio_config = speechsdk.audio.AudioConfig(filename=file)

        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        done = False

        def stop_cb(evt):
            """callback that stops continuous recognition upon receiving an event `evt`"""
            print('CLOSING on {}'.format(evt))
            speech_recognizer.stop_continuous_recognition()
            nonlocal done
            done = True

        all_results = []
        def handle_final_result(evt):
            all_results.append(evt.result.text)

        speech_recognizer.recognized.connect(handle_final_result)
        # Connect callbacks to the events fired by the speech recognizer
        speech_recognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt)))
        speech_recognizer.recognized.connect(lambda evt: print('RECOGNIZED: {}'.format(evt)))
        speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
        speech_recognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
        speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))
        
        # stop continuous recognition on either session stopped or canceled events
        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(stop_cb)

        # Start continuous speech recognition
        speech_recognizer.start_continuous_recognition()
        while not done:
            time.sleep(.5)

        print("Printing audio to text output")
        print(all_results)

        file_name = file + r"-speech-to-text-csv-output.txt"
        with open(file_name,"w") as fp:
            fp.writelines(all_results)

        blob_upload(file_name)

        print ("Audio File: "+file+" converted successfully")

    def blob_upload(localfilename):
        #blob_service_client = BlobServiceClient.from_connection_string(os.environ["blob_conn_str"])
        blob_client = blob_service_client.get_blob_client(container=output_container_name,blob=output_blob_filename)
        with open(localfilename, "rb") as data:
            blob_client.upload_blob(data, overwrite = True)        
        

    speech_recognize_continuous_from_file(input_audio_filename)