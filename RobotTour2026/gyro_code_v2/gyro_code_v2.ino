#include <Wire.h>
#include <EEPROM.h>
#include "ICM_20948.h"

class HeadingManager {
  private:
    ICM_20948_I2C _sensor;
    float _currentHeading = 0;
    float _gyroBiasZ = 0;
    unsigned long _lastTime = 0;
    float _offset = 0;
    float _smoothedHeading = 0;

    // Calibration State Variables
    bool _isCalibrating = false;
    long _calibrationCount = 0;
    float _calibrationSum = 0;
    long _targetSamples; // ~2.4 ms per sample

  public:
    void begin() {
      Wire.begin();
      Wire.setClock(400000);
      _sensor.begin(Wire, 1);
      _lastTime = micros();
    }

    // Trigger the start of calibration
    void startCalibration(long samples) {
      _isCalibrating = true;
      _calibrationCount = 0;
      _calibrationSum = 0;
      //Serial.println("STATUS: CALIBRATION_STARTED");

      _targetSamples = samples;
    }

    void update() {
      if (!_sensor.dataReady()) return;
      _sensor.getAGMT();

      if (_isCalibrating) {
        _calibrationSum += _sensor.gyrZ();
        _calibrationCount++;

        if (_calibrationCount >= _targetSamples) {
          _gyroBiasZ = _calibrationSum / _targetSamples;
          EEPROM.put(0, _gyroBiasZ); 
          _isCalibrating = false;
          //Serial.print("STATUS: CALIBRATION_COMPLETE | t="); Serial.println((micros()-_lastTime)/1000000, 3);
          _lastTime = micros();
        }
      } else {
        unsigned long now = micros();
        float dt = (now - _lastTime) / 1e6;
        _lastTime = now;

        float currentGyroZ = _sensor.gyrZ() - _gyroBiasZ;
        _currentHeading += currentGyroZ * dt;
        
        if (abs(currentGyroZ) > 0.05) {
          _smoothedHeading = _currentHeading;
        }
      }
    }

    void loadCalibration() {
      EEPROM.get(0, _gyroBiasZ);
      if (isnan(_gyroBiasZ)) _gyroBiasZ = 0;
    }

    float get_heading() { return _smoothedHeading - _offset; }
    bool is_calibrating() { return _isCalibrating; }
    void reset() { _offset = _smoothedHeading; }
};

HeadingManager gyro;

void setup() {
  Serial.begin(115200);
  gyro.begin();

  gyro.loadCalibration();
}

void loop() {
  gyro.update();

  if (Serial.available() > 0) {
    char cmd = Serial.read();
    
    if (gyro.is_calibrating()) {
      if (cmd == 'h') {
        Serial.println(777);
      } else if (cmd == 'i') {
        Serial.println("1");
      }
    } 
    else {
      // Normal command handling
      if (cmd == 'h') { 
        Serial.println(gyro.get_heading()); 
      } 
      else if (cmd == 'r') { 
        gyro.reset(); 
      } 
      else if (cmd == 'c') { // ex c5000 for calibration w/ 5000 samples
      long sampleCount = 40000;
        if (Serial.peek() >= '0' && Serial.peek() <= '9') {
          sampleCount = Serial.parseInt(); 
        }
        gyro.startCalibration(sampleCount); 
      }
      else if (cmd == 'i') {
        Serial.println("0");
      }
    }
  }
}