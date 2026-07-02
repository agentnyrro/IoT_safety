import paho.mqtt.client as mqtt
from picamera2 import Picamera2
from libcamera import Transform
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from picamera2.outputs import FfmpegOutput
import time
from datetime import datetime
import os
from minio import Minio
from threading import Thread

# MQTT data
broker_address = "[SERVER ADDRESS]"  
broker_port = 1883                      
broker_user = "[USERNAME]"           
broker_pass = "[PASSWORD]"

# Camera state
camera_is_recording = False

# Initialize camera
camera = Picamera2()
video_config = camera.create_video_configuration(
    main={"size": (640, 480), "format": "RGB888"},
    transform=Transform(rotation=180)
)
camera.configure(video_config)

start_time, end_time = None, None
current_filename = None

# MinIO
minio_client = Minio(
    "172.20.10.10:9000",
    access_key="admin",
    secret_key="adminpassword",
    secure=False
)

print(minio_client.list_buckets())
BUCKET = "recordings"

def upload_video(filepath):
    filename = os.path.basename(filepath)
    today = datetime.now()

    object_name = (
        f"{today.year}/"
        f"{today.month:02d}/"
        f"{today.day:02d}/"
        f"{filename}"
    )
    
    try:
        minio_client.fput_object(BUCKET, object_name, filepath, content_type="video/mp4")
        os.remove(filepath)
        print(f"Uploaded {filename}")
    except Exception as e:
        print(e)
        

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    client.subscribe("esp32/pir/status")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global camera_is_recording
    global start_time
    global end_time
    global current_filename
    
    print(msg.topic+" "+str(msg.payload))
    if msg.topic == "esp32/pir/status":
        if msg.payload == b"motion_detected" and not camera_is_recording:
            start_time = time.time() # record start time
            camera_is_recording = True
            current_filename = "/home/raspberry/Desktop/nagraniaPIR/" + time.strftime("%y%b%d_%H-%M-%S") + ".mp4"
            encoder = H264Encoder(bitrate=8_000_000)
            output = FfmpegOutput(current_filename)   # MP4
            camera.start_recording(encoder, output) 
        elif msg.payload == b"no_motion" and camera_is_recording:
            end_time = time.time() # record end time
            camera.stop_recording()
            camera_is_recording = False
            run_time = end_time - start_time
            print(f"Motion detected for {run_time} s")
            if run_time > 5:
                # Save to MinIO
                Thread(target=upload_video, args=(current_filename,),daemon=True).start()
            else:
                os.remove(current_filename)
            
def main():               
    # Connect to MQTT
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.username_pw_set(broker_user, broker_pass) 

    mqttc.connect(broker_address, broker_port)

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    mqttc.loop_forever(True)
    
if __name__ == "__main__":
    main()
