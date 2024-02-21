#include <AS5600.h>

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <AS5600.h>
AMS_5600 ams5600;
#define DIR_PIN2 2
int angle_in = 0;
// Đặc giá trị chân đầu ra cho TB6600 Driver
#define DIR_PIN 16   // Chân điều khiển hướng quay
#define STEP_PIN 17  // Chân điều khiển xung
const float DEG_PER_STEP = 0.45;  // Độ quay của mỗi bước xoay(Mỗi bước xoay 1.8 độ)
const int STEPS_PER_REV = 800;   // Số bước xoay cho một vòng quay 360 độ
int current_angle = 0;            // Góc hiện tại
int target_angle = 0;            // Góc mới cần đến
// Initialize wifi connection and MongoDB server
int value2; //Comparation value 
const char* ssid = "T.anh";
const char* password = "123456asd";
int Angle() {
  digitalWrite(DIR_PIN, LOW);
  int in;
  in = map(ams5600.getRawAngle(),0,4095,0,360);
  return in;
// }?><<
void setup() {

  Serial.begin(115200);
  Serial.println("***Lưu ý: Kết nối dây cho cảm biến và Driver TB6600 để chương trình hoạt động***");
  Serial.println("*************************Kiểm tra SSID và Password Wifi*************************");
  Wire.begin();
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN2, OUTPUT);
  while (Angle() != 0) {
  Serial.println(Angle());
  digitalWrite(DIR_PIN, LOW); // set chiều quay cho động cơ
  digitalWrite(STEP_PIN, HIGH);
  delayMicroseconds(2500);
  digitalWrite(STEP_PIN, LOW);
  delayMicroseconds(2500);
  }
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
}

unsigned long previousMillis = 0;

void loop() {

  unsigned long currentMillis = millis();
  //HTTP REQUEST
  if (currentMillis - previousMillis >= 500) {
  previousMillis = currentMillis;

  HTTPClient http;
  http.begin("https://ap-southeast-1.aws.data.mongodb-api.com/app/application-0-rxqgf/endpoint/getlatestdata");
  // KIỂM TRA REQUEST
  int httpCode = http.GET();
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    DynamicJsonDocument doc(50);
    deserializeJson(doc, payload);
    int value1 = doc[0]["angle"].as<int>();
//    Serial.println(payload);
    if  (value1 != value2){
      target_angle = value1;
      Serial.print("Giá trị góc đặt: ");
      Serial.println(value2);
      target_angle = value2;
    }
  }
  else {
    Serial.printf("HTTP error: %s\n", http.errorToString(httpCode).c_str());
    }
  http.end();
  }
    // Xoay stepper motor theo hướng 
// Xoay stepper motor theo hướng gần nhất
  if (target_angle != current_angle) {
  int clockwiseDistance = (target_angle - current_angle + 360) % 360;  // Khoảng cách thuận chiều kim đồng hồ
  int anticlockwiseDistance = (current_angle - target_angle + 360) % 360;  // Khoảng cách ngược chiều kim đồng hồ

  if (clockwiseDistance <= anticlockwiseDistance) {
    // Xoay theo chiều thuận kim đồng hồ
    digitalWrite(DIR_PIN, LOW);
    int steps = clockwiseDistance / DEG_PER_STEP;
    for (int i = 0; i < steps; i++) {
      digitalWrite(STEP_PIN, HIGH);
      delayMicroseconds(2500);
      digitalWrite(STEP_PIN, LOW);
      delayMicroseconds(2500);
    }
    current_angle = target_angle;
  } else {
    // Xoay theo chiều ngược kim đồng hồ
    digitalWrite(DIR_PIN, HIGH);
    int steps = anticlockwiseDistance / DEG_PER_STEP;
    for (int i = 0; i < steps; i++) {
      digitalWrite(STEP_PIN, HIGH);
      delayMicroseconds(2000);
      digitalWrite(STEP_PIN, LOW);
      delayMicroseconds(2000);
    }
    current_angle = target_angle;
  }
}

  if (ams5600.detectMagnet() == 1) {
      angle_in = Angle();
      Serial.println("   ");
      Serial.print("Giá trị góc của cảm biến AS5600: ");
      Serial.println(angle_in);
      Serial.print("Giá trị đặt: ");
      Serial.println(target_angle);
      Serial.println("   ");
    }

    int target_angleModified = target_angle;

    if ((target_angle == 0 || target_angle == 360) && (angle_in != 0 || angle_in != 360)) {
      target_angleModified = angle_in < 180 ? 0 : 360;
    }

    int error = target_angleModified - angle_in;

    if (error != 0 && error != 360 && error != -360) {
      int shortestDirection;

      if (error > 0) {
        shortestDirection = error <= 180 ? LOW : HIGH;
        Serial.print("Hệ thống bị thiếu: ");
        Serial.print(error);
        Serial.println(" độ");
      }
      else {
        shortestDirection = abs(error) <= 180 ? HIGH : LOW;
        Serial.print("Hệ thống bị dư: ");
        Serial.print(abs(error));
        Serial.println(" độ");
      }

      digitalWrite(DIR_PIN, shortestDirection);
      int steps_E = abs(error) / 0.45;

      for (int i = 0; i < steps_E; i++) {
        digitalWrite(STEP_PIN, HIGH);
        delayMicroseconds(2500);
        digitalWrite(STEP_PIN, LOW);
        delayMicroseconds(2500);
      }
    }

}