#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <AS5600.h>

AMS_5600 ams5600;

// Chân điều khiển hướng quay cho TB6600
#define DIR_PIN 16
// Chân điều khiển xung cho TB6600
#define STEP_PIN 17
// Chân điều khiển hướng quay khác (nếu cần)
#define DIR_PIN2 12

// Declare global variables
int targetAngle = 0;
int currentAngle = 0;
int currentAngle1 = 0;
int dir = 0;           // Initialize dir with a default value
int steps = 0;         // Initialize steps with a default value
int targetAngleFlag = 0;

// Initialize wifi connection and MongoDB server
const char* ssid = "T.anh";
const char* password = "123456asd";

unsigned long previousMillis = 0;

void setup() {
  Serial.begin(115200);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN2, OUTPUT);

  Serial.println("***Lưu ý: Kết nối dây cho cảm biến và Driver TB6600 để chương trình hoạt động***");
  Serial.println("*************************Kiểm tra SSID và Password Wifi*************************");

  Wire.begin();
  // pinMode(DIR_PIN, OUTPUT); // Không cần khai báo lại vì đã được khai báo ở trên
  // pinMode(STEP_PIN, OUTPUT); // Không cần khai báo lại vì đã được khai báo ở trên
  // pinMode(DIR_PIN2, OUTPUT); // Không sử dụng DIR_PIN2 trong đoạn mã, có thể loại bỏ

  // Wait for AS5600 to return to angle 0
  while (ams5600.getRawAngle() != 0) {
    Serial.println(ams5600.getRawAngle());
    digitalWrite(DIR_PIN, LOW);
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(1000);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(1000);
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= 2000) {
    // HTTP REQUEST
    HTTPClient http;
    http.begin("https://ap-southeast-1.aws.data.mongodb-api.com/app/application-0-rxqgf/endpoint/getdatacontrolarduino");

    // Check HTTP request
    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
      String payload = http.getString();
      DynamicJsonDocument doc(1024);
      deserializeJson(doc, payload);
      Serial.println(payload);

      // Corrected lines for accessing target_angle and current_angle
      targetAngle = doc["Public"]["Input"]["Data"]["target_angle"].as<int>();
      Serial.print("Giá trị góc đặt: ");
      Serial.println(targetAngle);

      currentAngle = doc["Public"]["Input"]["Data"]["current_angle"].as<int>();
      Serial.print("Giá trị góc hiện tại: ");
      Serial.println(currentAngle);

      dir = doc["Public"]["Output"]["jsondata"]["value"]["DIR"].as<int>();
      Serial.print("DIR: ");
      Serial.println(dir);

      steps = doc["Public"]["Output"]["jsondata"]["value"]["steps"].as<int>();
      Serial.print("steps: ");
      Serial.println(steps);
    } else {
      Serial.printf("HTTP error: %s\n", http.errorToString(httpCode).c_str());
    }
    http.end();
    previousMillis = currentMillis;
  }

  // Rotate to the target angle
  if (targetAngle != currentAngle1) {
    int dir1 = (dir == 0) ? HIGH : LOW;
    digitalWrite(DIR_PIN, dir1);

    for (int i = 0; i < steps; i++) {
      digitalWrite(STEP_PIN, HIGH);
      delayMicroseconds(2500);
      digitalWrite(STEP_PIN, LOW);
      delayMicroseconds(2500);
    }

    currentAngle = targetAngle;
    currentAngle1 = targetAngle;
  }

  // Detect magnet and update angle_in
  if (ams5600.detectMagnet() == 1) {
    int angle_in = ams5600.getRawAngle();
    Serial.print("Giá trị góc của cảm biến AS5600: ");
    Serial.println(angle_in);
  }

  // Adjust the angle if needed
  int error = currentAngle1 - ams5600.getRawAngle();
  if (error != 0) {
    int shortestDirection = (error > 0) ? HIGH : LOW;

    digitalWrite(DIR_PIN, shortestDirection);
    int steps_E = abs(error) / 0.45;

    for (int i = 0; i < steps_E; i++) {
      digitalWrite(STEP_PIN, HIGH);
      delayMicroseconds(2500);
      digitalWrite(STEP_PIN, LOW);
      delayMicroseconds(2500);
    }
  }

  delay(1000);
}
