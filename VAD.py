
####### Code đa qua chinh sua
import sys
from tuning import Tuning
import usb.core
import usb.util
import pymongo
import time
import pyaudio
import wave
from datetime import datetime
import librosa
import librosa.display
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
from keras.models import load_model
from pymongo import MongoClient
from usb import core as usb_core
from bson import ObjectId  
from datetime import datetime
import time

# Định nghĩa class labels
class_labels = {0:'dog',1:'bird',2:'cow',3: 'bird'}

def predict_from_audio(file_path, model, confidence_threshold=0.7):
    y, sr = librosa.load(file_path, sr=None)
    mels = librosa.feature.melspectrogram(y=y, sr=sr)
    mels_db = librosa.power_to_db(mels, ref=np.max)
    
    plt.figure(figsize=(3, 3))
    librosa.display.specshow(mels_db, sr=sr)
    plt.axis('off')
    plt.savefig('tmp.png')
    plt.close()
    
    img = Image.open('tmp.png').resize((1, 80))
    img_array = np.array(img)[..., :1]
    img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    prediction = model.predict(img_array)
    max_probability = np.max(prediction)
    
    if max_probability >= confidence_threshold:
        predicted_index = np.argmax(prediction)
        predicted_class = class_labels[predicted_index]
        print(f"This audio is a   {predicted_class}    with confidence {max_probability}")
        return predicted_class
    else:
        print(f"This audio does not meet the confidence threshold ({confidence_threshold})")
        return None

# Hàm ghi âm
def record_audio(duration=5, filename='temp.wav'):
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100
    CHUNK = 1024
    RECORD_SECONDS = duration
    WAVE_OUTPUT_FILENAME = filename

    audio = pyaudio.PyAudio()

    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    print("Recording...")
    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    print("Finished recording.")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    waveFile.setnchannels(CHANNELS)
    waveFile.setsampwidth(audio.get_sample_size(FORMAT))
    waveFile.setframerate(RATE)
    waveFile.writeframes(b''.join(frames))
    waveFile.close()


# Kết nối đến MongoDB Atlas
client = MongoClient("mongodb+srv://Phamtienanh0:Phamtienanh0@cluster0.o3w7mgf.mongodb.net/?retryWrites=true&w=majority")
db = client['data']
collection = db['testjson']

# Khởi tạo USB device và đối tượng Tuning
dev = usb_core.find(idVendor=0x2886, idProduct=0x0018)
if dev:
    Mic_tuning = Tuning(dev)
    Mic_tuning.set_vad_threshold(2)
else:
    print("USB device not found. Exiting...")
    sys.exit(1)


model = load_model('model_final3.h5')


# Hàm ghi âm và dự đoán
def record_and_predict_audio(model, Mic_tuning, collection):
    old_direction = None
    is_changed = False
    sampling_interval = 1

    while True:
        try:
            if Mic_tuning.is_voice() == 1:
                direction = 360 - Mic_tuning.direction
                if direction != old_direction:
                    print(old_direction)
                    timestamp = datetime.now()
                    record_audio(duration=4, filename='temp.wav')
                    prediction = predict_from_audio('temp.wav', model, confidence_threshold=0.7)

                    if prediction is not None:
                        # Điều kiện để xác định tài liệu cần cập nhật
                        filter_condition = {"_id": ObjectId("658bdd3ff9f37d4e78fb5350")}

                        # Biểu thức cập nhật
                        update_expression = {
                            "$set": {
                                "Public.Input.Data.Time": timestamp,
                                "Public.Input.Data.target_angle": direction,
                                "Public.Input.Data.current_angle": old_direction,
                                "Public.Input.Data.Prediction": prediction
                            }
                        }

                        # Thực hiện cập nhật
                        result = collection.update_one(filter_condition, update_expression)

                        print("Stored information in MongoDB.")
                        is_changed = True

                if is_changed:
                    print("Latest angle value:", direction)
                    is_changed = False

                old_direction = direction
            time.sleep(sampling_interval)
        except KeyboardInterrupt:
            print("Exiting...")
            break

# Gọi hàm để ghi âm và dự đoán
record_and_predict_audio(model, Mic_tuning, collection)

# Đóng kết nối MongoDB khi kết thúc
client.close()