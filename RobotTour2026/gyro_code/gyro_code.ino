#include <Wire.h>
#include "ICM_20948.h"

float q0 = 1, q1 = 0, q2 = 0, q3 = 0;
// Mahony gains (tune these)
// Increase Ki slightly to "learn" the bias. 
// 0.001 to 0.01 is a good starting range for slow bias correction.
float twoKp = 2.0f * 0.5f;   
float twoKi = 2.0f * 0.005f; 
float integralFBx = 0, integralFBy = 0, integralFBz = 0;

void Mahony6DOFUpdate(float gx, float gy, float gz,
                      float ax, float ay, float az,
                      float dt) {
  float recipNorm;
  float vx, vy, vz;
  float ex, ey, ez;

  // 1. Normalize accelerometer
  float a_norm = sqrt(ax*ax + ay*ay + az*az);
  if (a_norm == 0.0f) return; // Prevent NaN
  recipNorm = 1.0f / a_norm;
  ax *= recipNorm; ay *= recipNorm; az *= recipNorm;

  // 2. Estimated direction of gravity (from current quaternion)
  vx = 2.0f * (q1*q3 - q0*q2);
  vy = 2.0f * (q0*q1 + q2*q3);
  vz = q0*q0 - q1*q1 - q2*q2 + q3*q3;

  // 3. Error is cross product between estimated and measured gravity
  ex = (ay * vz - az * vy);
  ey = (az * vx - ax * vz);
  ez = (ax * vy - ay * vx);

  // 4. Compute and apply integral feedback (The "Learning" part)
  // We only apply this if Ki > 0
  if(twoKi > 0.0f) {
    integralFBx += twoKi * ex * dt;
    integralFBy += twoKi * ey * dt;
    integralFBz += twoKi * ez * dt;
    gx += integralFBx;
    gy += integralFBy;
    gz += integralFBz;
  }

  // 5. Apply proportional feedback
  gx += twoKp * ex;
  gy += twoKp * ey;
  // Note: We don't apply 'ez' to 'gz' here because 
  // accelerometer can't sense yaw error.

  // 6. Integrate rate of change of quaternion
  gx *= (0.5f * dt);
  gy *= (0.5f * dt);
  gz *= (0.5f * dt);

  float qa = q0, qb = q1, qc = q2, qd = q3;
  q0 += (-qb * gx - qc * gy - qd * gz);
  q1 += (qa * gx + qc * gz - qd * gy);
  q2 += (qa * gy - qb * gz + qd * gx);
  q3 += (qa * gz + qb * gy - qc * gx);

  // 7. Normalize quaternion
  recipNorm = 1.0f / sqrt(q0*q0 + q1*q1 + q2*q2 + q3*q3);
  q0 *= recipNorm; q1 *= recipNorm; q2 *= recipNorm; q3 *= recipNorm;
}

void MahonyUpdate(float gx, float gy, float gz,
                  float ax, float ay, float az,
                  float mx, float my, float mz,
                  float dt) {

  float recipNorm;
  float hx, hy, bx, bz;
  float vx, vy, vz, wx, wy, wz;
  float ex, ey, ez;

  // Normalize accelerometer
  recipNorm = 1.0f / sqrt(ax * ax + ay * ay + az * az);
  ax *= recipNorm; ay *= recipNorm; az *= recipNorm;

  // Normalize magnetometer (might down-weight later..)
  recipNorm = 1.0f / sqrt(mx * mx + my * my + mz * mz);
  mx *= recipNorm; my *= recipNorm; mz *= recipNorm;

  // Reference direction of Earth's magnetic field
  hx = 2.0f * mx * (0.5f - q2*q2 - q3*q3) +
       2.0f * my * (q1*q2 - q0*q3) +
       2.0f * mz * (q1*q3 + q0*q2);
  hy = 2.0f * mx * (q1*q2 + q0*q3) +
       2.0f * my * (0.5f - q1*q1 - q3*q3) +
       2.0f * mz * (q2*q3 - q0*q1);
  bx = sqrt(hx * hx + hy * hy);
  bz = 2.0f * mx * (q1*q3 - q0*q2) +
       2.0f * my * (q2*q3 + q0*q1) +
       2.0f * mz * (0.5f - q1*q1 - q2*q2);

  // Estimated direction of gravity and magnetic field
  vx = 2.0f * (q1*q3 - q0*q2);
  vy = 2.0f * (q0*q1 + q2*q3);
  vz = q0*q0 - q1*q1 - q2*q2 + q3*q3;

  wx = 2.0f * bx * (0.5f - q2*q2 - q3*q3) + 2.0f * bz * (q1*q3 - q0*q2);
  wy = 2.0f * bx * (q1*q2 - q0*q3) + 2.0f * bz * (q0*q1 + q2*q3);
  wz = 2.0f * bx * (q0*q2 + q1*q3) + 2.0f * bz * (0.5f - q1*q1 - q2*q2);

  // Error (cross product of estimated vs actual)
  ex = (ay * vz - az * vy) + (my * wz - mz * wy);
  ey = (az * vx - ax * vz) + (mz * wx - mx * wz);
  ez = (ax * vy - ay * vx) + (mx * wy - my * wx);

  // Applying feedback
  gx += twoKp * ex;
  gy += twoKp * ey;
  gz += twoKp * ez;

  // Quaternion generation
  gx *= 0.5f * dt;
  gy *= 0.5f * dt;
  gz *= 0.5f * dt;

  float qa = q0, qb = q1, qc = q2;
  q0 += (-qb * gx - qc * gy - q3 * gz);
  q1 += (qa * gx + qc * gz - q3 * gy);
  q2 += (qa * gy - qb * gz + q3 * gx);
  q3 += (qa * gz + qb * gy - qc * gx);

  recipNorm = 1.0f / sqrt(q0*q0 + q1*q1 + q2*q2 + q3*q3);
  q0 *= recipNorm; q1 *= recipNorm; q2 *= recipNorm; q3 *= recipNorm;
}

class HeadingManager {
  private:
    ICM_20948_I2C _sensor;
    float _currentHeading = 0;
    float _gyroBiasZ = 0;
    unsigned long _lastTime = 0;
    float _offset = 0;

    float _smoothedHeading = 0;
    float _alpha = 0.9;

  public:
    void begin() {
      Wire.begin();
      Wire.setClock(400000);
      
      Serial.println("Checking for ICM-20948...");

      bool initialized = false;
      while (!initialized) {
        // Try both possible I2C addresses (0x69 and 0x68)
        // SparkFun boards usually use 1 (0x69)
        _sensor.begin(Wire, 1); 
        
        if (_sensor.status == ICM_20948_Stat_Ok) {
          Serial.println("Sensor found at 0x69!");
          initialized = true;
        } else {
          _sensor.begin(Wire, 0); 
          if (_sensor.status == ICM_20948_Stat_Ok) {
            Serial.println("Sensor found at 0x68!");
            initialized = true;
          } else {
            Serial.println("Sensor not found. Check wiring (A4/A5) and power. Retrying...");
            delay(1000);
          }
        }
      }

      calibrate();
      /*
      Serial.println("Starting...");
      bool initCompleted = false;
      int initBuffer = 10;
      int delayMS = 10;
      for (int i=0; i<(initBuffer*1000 / delayMS); i++) {
        update();
        delay(10);
      }
      */
    }

    void calibrate() {
      float totalZ = 0;
      const long samples = 100; // around 2.4ms per sample... used to be 25000
      long count = 0;
      bool done = false;
      unsigned long now = micros();
      Serial.print("Calibrating... Keep still for ~"); Serial.print(samples*1.5/1000, 1); Serial.println("s!");
      while (!done) {
        if (_sensor.dataReady()) {
          _sensor.getAGMT();
          totalZ += _sensor.gyrZ();
          count += 1;
          if (count%1000 == 0) {
            Serial.print(count/1000); Serial.print(" ");
          }
          if (count >= samples) {
            done = true;
          }
        } else {
          delayMicroseconds(200);
        }
      }
      _gyroBiasZ = totalZ / samples;
      _lastTime = micros();
      Serial.print("Calibration complete ("); Serial.print(_lastTime - now); Serial.print(").");
    }

    void update() {
      if (_sensor.dataReady()) {
        _sensor.getAGMT();
        unsigned long now = micros();
        float dt = (now - _lastTime) / 1e6;
        _lastTime = now;

        /*
        float gx = _sensor.gyrX() * DEG_TO_RAD;
        float gy = _sensor.gyrY() * DEG_TO_RAD;
        float gz = (_sensor.gyrZ() - _gyroBiasZ) * DEG_TO_RAD;

        float ax = _sensor.accX();
        float ay = _sensor.accY();
        float az = _sensor.accZ();
        
        float mx = _sensor.magX();
        float my = _sensor.magY();
        float mz = _sensor.magZ();
        
        //MahonyUpdate(gx, gy, gz, ax, ay, az, mx, my, mz, dt);
        Mahony6DOFUpdate(gx, gy, gz, ax, ay, az, dt);

        float yaw = atan2(2.0f * (q0*q3 + q1*q2), 1.0f - 2.0f * (q2*q2 + q3*q3));
        _currentHeading = yaw * RAD_TO_DEG;
        _smoothedHeading = _alpha * _smoothedHeading + (1 - _alpha) * _currentHeading;
        */

        float currentGyroZ = _sensor.gyrZ() - _gyroBiasZ;
        _currentHeading += currentGyroZ * dt;
        if (abs(currentGyroZ) > 0.05) {
          _smoothedHeading = _currentHeading;
        }
      }
    }

    float getHeading() { return _smoothedHeading - _offset; }
    float getRawHeading() { return _currentHeading; }
    void reset() { _offset = _smoothedHeading; }
};

HeadingManager gyro;
#define SLAVE_ADDRESS 0x04
#define CMD_RESET 0x01
#define CMD_CALIBRATE 0x02

void receiveEvent(int howMany) {
  while (Wire.available()) {
    byte cmd = Wire.read();
    if (cmd == CMD_RESET) {
      gyro.reset();
    } else if (cmd == CMD_CALIBRATE) {
      gyro.calibrate();
    }
  }
}

void requestEvent() {
  float currentHeading = gyro.getHeading();
  
  // split the 4-byte float into a byte array to send over I2C
  byte* bytePointer = (byte*)(void*)&currentHeading;
  Wire.write(bytePointer, 4); 
}

void setup() {
  Serial.begin(115200);
  gyro.begin();

  Wire.begin(SLAVE_ADDRESS);
  Wire.onReceive(receiveEvent);   // reset or calibrate command from ev3
  Wire.onRequest(requestEvent);   // sending heading data
  
  gyro.reset();
  Serial.println("Gyro initialized");
}

//unsigned long firstTime = millis();
void loop() {
  gyro.update();
  Serial.println(gyro.getHeading());
  /*
  unsigned long now = millis();
  if (((now-firstTime)%3000) == 0) {
    Serial.print(gyro.getHeading()); Serial.print("d  |  "); Serial.print((now-firstTime)/1000, 1); Serial.print("s  |  "); Serial.print((gyro.getHeading()*1000)/(now-firstTime), 6); Serial.println("d/s");
  }
  */
}