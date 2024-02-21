import sys
import time
import pyaudio
import wave
from datetime import datetime
import librosa
import tensorflow as tf
import numpy as np
from pymongo import MongoClient
from usb import core as usb_core
from bson import ObjectId
from tuning import Tuning
from tensorflow.image import resize
import speech_recognition as sr

class_labels = {0: 'cat', 1: 'dog'}
model = tf.keras.models.load_model('audio_classification_model.hdf5')

# Connect to MongoDB Atlas
client = MongoClient("mongodb+srv://Phamtienanh0:Phamtienanh0@cluster0.o3w7mgf.mongodb.net/?retryWrites=true&w=majority")
db = client['data']
collection = db['testjson']

def record_audio(duration=5, filename='temp.wav'):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
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

def predict_from_audio(audio_data, model, confidence_threshold=0.85):
    sample_rate = 44100
    mel_spectrogram = librosa.feature.melspectrogram(y=audio_data, sr=sample_rate)
    mel_spectrogram = resize(np.expand_dims(mel_spectrogram, axis=-1), (128, 128))
    mel_spectrogram = tf.reshape(mel_spectrogram, (1, 128, 128, 1))
    prediction = model.predict(mel_spectrogram)
    predicted_index = np.argmax(prediction)
    
    if prediction[0][predicted_index] >= confidence_threshold:
        predicted_class = class_labels[predicted_index]
        print("Predicted class:", predicted_class)
        return predicted_class
    else:
        print("Prediction confidence below threshold")
        return None



def audio_mode():
    # Initialize USB device and Tuning object
    dev = usb_core.find(idVendor=0x2886, idProduct=0x0018)
    if dev:
        Mic_tuning = Tuning(dev)
        Mic_tuning.set_vad_threshold(10)
    else:
        print("USB device not found. Exiting...")
        sys.exit(1)

    old_direction = None
    is_changed = False
    sampling_interval = 2

    while True:
        try:
            if Mic_tuning.is_voice() == 1:
                direction = 360 - Mic_tuning.direction
                if direction != old_direction:
                    timestamp = datetime.now()
                    record_audio(duration=4, filename='temp.wav')
                    audio_data, _ = librosa.load('temp.wav', sr=None)
                    prediction = predict_from_audio(audio_data, model)

                    if prediction is not None:
                        filter_condition = {"_id": ObjectId("658bdd3ff9f37d4e78fb5350")}
                        update_expression = {
                            "$set": {
                                "Public.Input.Data.Time": timestamp,
                                "Public.Input.Data.target_angle": direction,
                                "Public.Input.Data.current_angle": old_direction,
                                "Public.Input.Data.Prediction": prediction,
                                "Public.Input.Data.command": None
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
            print("Exiting audio mode...")
            break

def recognize_speech_command():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Say command...")
        audio = recognizer.listen(source)

    try:
        command = recognizer.recognize_google(audio, language="en-US")
        print("You said:", command)
        return command.lower()
    except sr.UnknownValueError:
        print("Could not understand audio")
        return None
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))
        return None
    

def speech_command_mode():
    # Đặt góc ban đầu về 0
    target_angle = 0
    previous_target_angle = 0
    step_value = 0
    while True:
        try:
            speech_command = recognize_speech_command()

            if speech_command:
                # Khởi tạo USB device và Tuning object
                dev = usb_core.find(idVendor=0x2886, idProduct=0x0018)
                if dev:
                    Mic_tuning = Tuning(dev)
                    Mic_tuning.set_vad_threshold(2)
                else:
                    print("USB device not found. Exiting...")
                    sys.exit(1)

                dir_value = None
                
                if speech_command == "back": # cập nhật Step vào trường value.steps
                    print("False command recognized")
                    previous_target_angle = target_angle
                    target_angle -= 90
                    target_angle %= 360  # Đảm bảo góc luôn nằm trong phạm vi từ 0 đến 359 độ

                elif speech_command == "front": # cập nhật Step vào trường value.steps
                    print("True command recognized")
                    previous_target_angle = target_angle
                    target_angle += 90
                    target_angle %= 360  # Đảm bảo góc luôn nằm trong phạm vi từ 0 đến 359 độ

                elif speech_command == "clockwise": # cập nhật Step vào trường value.steps_command
                    print("Clockwise command recognized")
                    dir_value = 0
                    step_value = 1

                elif speech_command == "counterclockwise": # cập nhật Step vào trường value.steps_command
                    print("Counterclockwise command recognized")
                    dir_value = 1
                    step_value = 2

                elif speech_command == "stop":
                    print("Stop command recognized")
                    step_value = 3

                else:
                    print("Unrecognized speech command:", speech_command)
                    continue

                # Lưu thông tin vào MongoDB
                timestamp = datetime.now()
                filter_condition = {"_id": ObjectId("658bdd3ff9f37d4e78fb5350")}
                update_expression = {
                    "$set": {
                        "Public.Input.Data.Time": timestamp,
                        "Public.Input.Data.Prediction": None,
                        "Public.Input.Data.target_angle": target_angle,
                        "Public.Input.Data.current_angle": previous_target_angle,
                        "Public.Input.Data.command": speech_command,
                        "Public.Output.jsondata.value.steps_command": step_value
                    }
                }

                if speech_command is not None:
                    
                    update_expression["$set"]["Public.Output.jsondata.value.DIR"] = dir_value

                result = collection.update_one(filter_condition, update_expression)

                # Hiển thị góc hoặc giá trị DIR sau khi nhận lệnh
                print(f"Updated angle: {target_angle} - Updated DIR: {dir_value} - Updated steps_command: {step_value}")

        except KeyboardInterrupt:
            print("Exiting speech command mode...")
            break


def main():
    mode_running = None

    while True:
        print("Choose mode:")
        print("1. Cat & Dog classification mode")
        print("2. Speech command mode")
        print("0. Exit")
        choice = input("Choose mode: ")

        if choice == "1":
            if mode_running == "audio":
                print("Classification mode is already running.")
            else:
                print("Entering classification mode...")
                mode_running = "audio"
                audio_mode()
        elif choice == "2":
            if mode_running == "speech":
                print("Speech command mode is already running.")
            else:
                print("Entering speech command mode...")
                mode_running = "speech"
                speech_command_mode()
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please enter again.")

    client.close()

if __name__ == "__main__":
    main()
