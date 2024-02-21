import numpy as np
import librosa
import pyaudio
import wave
from keras.models import load_model
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import time

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
from bson import ObjectId  # Add this import
from datetime import datetime
import time
# Định nghĩa class labels
class_labels = {0:'bird', 1:'cat', 2:'dog', 3:'cow'}

# def extract_feature(file_name, max_pad_len=80):
#     try:
#         audio_data, sample_rate = librosa.load(file_name, res_type='kaiser_fast')
#         # Sửa đổi ở đây: sử dụng max_pad_len thay vì cố định là 40
#         mfccs = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=max_pad_len)
#         if mfccs.shape[1] > max_pad_len:
#             mfccs = mfccs[:, :max_pad_len]
#         elif mfccs.shape[1] < max_pad_len:
#             pad_width = max_pad_len - mfccs.shape[1]
#             mfccs = np.pad(mfccs, pad_width=((0, 0), (0, pad_width)), mode='constant')
#     except Exception as e:
#         print("Could not process file: ", file_name)
#         return None 
#     return mfccs.mean(axis=1)

# def extract_feature(file_name, max_pad_len=80):
#     try:
#         audio_data, sample_rate = librosa.load(file_name, res_type='kaiser_fast')
#         mfccs = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=max_pad_len)
#         if (mfccs.shape[1] > max_pad_len):
#             mfccs = mfccs[:, :max_pad_len]
#         elif (mfccs.shape[1] < max_pad_len):
#             pad_width = max_pad_len - mfccs.shape[1]
#             mfccs = np.pad(mfccs, pad_width=((0, 0), (0, pad_width)), mode='constant')
#     except Exception as e:
#         print("Could not process file: ", file_name)
#         return None
#     return mfccs.mean(axis=1)

def extract_feature(file_name, max_pad_len=80):
    try:
        audio_data, sample_rate = librosa.load(file_name, res_type='kaiser_fast')
        mfccs = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=max_pad_len)
        print(f'MFCCs shape before padding/trimming: {mfccs.shape}')
        if (mfccs.shape[1] > max_pad_len):
            mfccs = mfccs[:, :max_pad_len]
        elif (mfccs.shape[1] < max_pad_len):
            pad_width = max_pad_len - mfccs.shape[1]
            mfccs = np.pad(mfccs, pad_width=((0, 0), (0, pad_width)), mode='constant')
        print(f'MFCCs shape after padding/trimming: {mfccs.shape}')
    except Exception as e:
        print(f"Could not process file: {file_name}, Error: {e}")
        return None
    return mfccs.mean(axis=1)
def predict_from_audio(file_path, model, confidence_threshold=0.7):
    mfccs = extract_feature(file_path)
    if mfccs is None:
        print("Error in feature extraction")
        return None
    mfccs_reshaped = mfccs.reshape(1, 80, 1, 1)
    prediction = model.predict(mfccs_reshaped)
    predicted_index = np.argmax(prediction)
    
    # Kiểm tra ngưỡng tự tin
    if prediction[0][predicted_index] >= confidence_threshold:
        predicted_class = class_labels[predicted_index]
        print("Predicted class:", predicted_class)
        return predicted_class
    else:
        print("Prediction confidence below threshold")
        return None

# def predict_from_audio(file_path, model, max_pad_len=80, confidence_threshold=0.7):
#     # Trích xuất đặc trưng từ đường dẫn file
#     mfccs = extract_feature(file_path, max_pad_len)
#     if mfccs is None:
#         print("Error in feature extraction")
#         return None
#     mfccs_reshaped = mfccs.reshape(1, max_pad_len, 1, 1)
#     prediction = model.predict(mfccs_reshaped)
#     predicted_index = np.argmax(prediction)
    
#     # Kiểm tra ngưỡng tự tin
#     if prediction[0][predicted_index] >= confidence_threshold:
#         predicted_class = class_labels[predicted_index]
#         print(f"Predicted class: {predicted_class} with confidence: {prediction[0][predicted_index]}")
#         return predicted_class
#     else:
#         print("Prediction confidence below threshold")
#         return None


# Hàm ghi âm
def record_audio(duration=5, filename='temp.wav'):
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 16000
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
    Mic_tuning.set_vad_threshold(4)
else:
    print("USB device not found. Exiting...")
    sys.exit(1)

# Tải mô hình
model = load_model('D:/data4/model_final3.h5')
# Cập nhật hàm record_and_predict_audio để cải thiện việc xác định hướng
def record_and_predict_audio(model, Mic_tuning, collection, confidence_threshold=0.6):
    old_direction = None
    is_changed = False
    sampling_interval = 2

    while True:
        try:
            if Mic_tuning.is_voice() == 1:
                direction = 360 - Mic_tuning.direction
                if direction != old_direction:
                    print(old_direction)
                    timestamp = datetime.now()
                    record_audio(duration=4, filename='temp.wav')
                    prediction = predict_from_audio('temp.wav', model, confidence_threshold)  # Truyền confidence_threshold vào đây

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
        except Exception as e:
            print(f"An error occurred: {e}")
            # Thêm bất kỳ xử lý lỗi cụ thể nào ở đây
            break

# Gọi hàm để ghi âm và dự đoán
record_and_predict_audio(model, Mic_tuning, collection, confidence_threshold=0.6)  # Truyền confidence_threshold vào đây

# Đóng kết nối MongoDB khi kết thúc
client.close()
