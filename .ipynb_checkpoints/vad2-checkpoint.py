import sys
import time
import pyaudio
import wave
from datetime import datetime
import librosa
import tensorflow as tf
import numpy as np
from keras.layers import Input, Conv2D, MaxPooling2D, Flatten, Dense
from keras.models import Model
from keras.optimizers import Adam
from sklearn.model_selection import train_test_split
from keras.utils import to_categorical
# from keras.preprocessing.image import resize
from keras.models import load_model
from pymongo import MongoClient
from usb import core as usb_core
from bson import ObjectId
from tuning import Tuning
from tensorflow.image import resize

# # Define your folder structure
# data_dir = 'training_data'
# classes = ['cat', 'dog']

# # Define class labels based on the classes list
# class_labels = {i: class_name for i, class_name in enumerate(classes)}
class_labels = {0: 'cat', 1: 'dog'}

# Load the model
model = load_model('audio_classification_model.hdf5')

# Connect to MongoDB Atlas
client = MongoClient("mongodb+srv://Phamtienanh0:Phamtienanh0@cluster0.o3w7mgf.mongodb.net/?retryWrites=true&w=majority")
db = client['data']
collection = db['testjson']

# Initialize USB device and Tuning object
dev = usb_core.find(idVendor=0x2886, idProduct=0x0018)
if dev:
    Mic_tuning = Tuning(dev)
    Mic_tuning.set_vad_threshold(1)
else:
    print("USB device not found. Exiting...")
    sys.exit(1)

# Function to record audio
def record_audio(duration=5, filename='temp.wav'):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1  # Use 1 channel since there's only one microphone
    RATE = 44100  # Adjust sample rate according to your microphone's sample rate
    CHUNK = 2048
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

# Function to predict from audio
def predict_from_audio(audio_data, model, confidence_threshold=0.7):
    sample_rate = 44100  # Adjust according to your microphone's sample rate
    mel_spectrogram = librosa.feature.melspectrogram(y=audio_data, sr=sample_rate)
    mel_spectrogram = resize(np.expand_dims(mel_spectrogram, axis=-1), (128, 128))
    mel_spectrogram = tf.reshape(mel_spectrogram, (1, 128, 128, 1))
    prediction = model.predict(mel_spectrogram)
    predicted_index = np.argmax(prediction)
    
    # Check confidence threshold
    if prediction[0][predicted_index] >= confidence_threshold:
        predicted_class = class_labels[predicted_index]
        print("Predicted class:", predicted_class)
        return predicted_class
    else:
        print("Prediction confidence below threshold")
        return None

# Function to record audio and predict
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
                    audio_data, _ = librosa.load('temp.wav', sr=None)
                    prediction = predict_from_audio(audio_data, model, confidence_threshold)

                    if prediction is not None:
                        filter_condition = {"_id": ObjectId("658bdd3ff9f37d4e78fb5350")}
                        update_expression = {
                            "$set": {
                                "Public.Input.Data.Time": timestamp,
                                "Public.Input.Data.target_angle": direction,
                                "Public.Input.Data.current_angle": old_direction,
                                "Public.Input.Data.Prediction": prediction
                            }
                        }
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

# Call the function to record and predict
record_and_predict_audio(model, Mic_tuning, collection, confidence_threshold=0.6)

# Close MongoDB connection
client.close()