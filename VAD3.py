import numpy as np
import librosa
import pyaudio
import wave
from keras.models import load_model
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import time
import usb.core
import usb.util
import sys

# Nếu 'Tuning' được cung cấp bởi một thư viện ngoài, hãy đảm bảo đã nhập chính xác
from tuning import Tuning

# Định nghĩa class labels
class_labels = {0: 'bird', 1: 'cat', 2: 'dog', 3: 'cow'}

# Hàm trích xuất đặc trưng MFCC
def extract_feature(file_name, max_pad_len=80):
    try:
        audio_data, sample_rate = librosa.load(file_name, res_type='kaiser_fast')
        mfccs = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=max_pad_len)
        if mfccs.shape[1] > max_pad_len:
            mfccs = mfccs[:, :max_pad_len]
        elif mfccs.shape[1] < max_pad_len:
            pad_width = max_pad_len - mfccs.shape[1]
            mfccs = np.pad(mfccs, pad_width=((0, 0), (0, pad_width)), mode='constant')
    except Exception as e:
        print(f"Could not process file: {file_name}, Error: {e}")
        return None
    return mfccs.mean(axis=1)

# Hàm dự đoán từ âm thanh
def predict_from_audio(file_path, model, confidence_threshold=0.7):
    mfccs = extract_feature(file_path)
    if mfccs is None:
        print("Error in feature extraction")
        return None
    mfccs_reshaped = mfccs.reshape(1, 80, 1, 1)
    prediction = model.predict(mfccs_reshaped)
    predicted_index = np.argmax(prediction)
    
    if prediction[0][predicted_index] >= confidence_threshold:
        predicted_class = class_labels[predicted_index]
        print("Predicted class:", predicted_class)
        return predicted_class
    else:
        print("Prediction confidence below threshold")
        return None

# Hàm ghi âm
def record_audio(duration=4, filename='temp.wav'):
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

# Khởi tạo kết nối MongoDB
client = MongoClient("mongodb+srv://Phamtienanh0:Phamtienanh0@cluster0.o3w7mgf.mongodb.net/?retryWrites=true&w=majority")
db = client['data']
collection = db['testjson']

# Khởi tạo USB device và đối tượng Tuning
dev = usb.core.find(idVendor=0x2886, idProduct=0x0018)
if dev is None:
    print("USB device not found. Exiting...")
    sys.exit(1)
Mic_tuning = Tuning(dev)
Mic_tuning.set_vad_threshold(4)

# Tải mô hình
model = load_model('D:/data4/model_final3.h5')

try:
    # Ghi âm và dự đoán
    record_audio()
    predicted_class = predict_from_audio('temp.wav', model)

    # Lưu kết quả vào MongoDB
    if predicted_class is not None:
        result = {
            'predicted_class': predicted_class,
            'timestamp': datetime.now()
        }
        collection.insert_one(result)
        print("Result saved to MongoDB")
    else:
        print("No prediction made")
except KeyboardInterrupt:
    print("Exiting...")
except Exception as e:
    print(f"An error occurred: {e}")
finally:

    # Đóng kết nối MongoDB khi kết thúc
    client.close()
