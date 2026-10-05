#include <Wire.h>
#include <EEPROM.h>
#include "ICM_20948.h"

// EEPROM layout: [0..3] = biasA (float), [4..7] = biasB (float)
static constexpr int EEPROM_ADDR_A = 0;
static constexpr int EEPROM_ADDR_B = 4;

// --- Tuning constants ---
static constexpr float MOTION_THRESHOLD      = 0.9f;   // °/s rolling mean — below = stationary
static constexpr float ZUPT_VAR_THRESHOLD    = 3.0f;   // (°/s)² variance  — below = stationary
static constexpr float ZUPT_ALPHA            = 0.003f; // EMA correction rate; smaller = slower/stabler
static constexpr int   ZUPT_WINDOW           = 8;      // rolling window size (power of 2); smaller = more responsive
static constexpr int   MOTION_LOCKOUT_SAMPLES = 128;    // samples to stay in motion mode after turn ends

class HeadingManager {
private:
    ICM_20948_I2C _sensor;

    // --- Heading state ---
    float         _heading    = 0;
    float         _offset     = 0;
    unsigned long _lastTime   = 0;

    // --- Linear drift model: bias(t) = _biasA + _biasB * seconds_since_cal_end ---
    float         _biasA      = 0;  // intercept (°/s)
    float         _biasB      = 0;  // slope     (°/s per s)
    unsigned long _calEndTime = 0;

    // --- Debug ---
    float _lastVar       = 0;
    float _lastCorrected = 0;

    // --- Calibration (online linear regression) ---
    bool          _isCalibrating = false;
    long          _targetSamples = 0;
    long          _calCount      = 0;
    double        _sumT = 0, _sumT2 = 0;
    double        _sumY = 0, _sumTY = 0;
    unsigned long _calStartTime  = 0;

    // --- ZUPT: variance-based zero-motion detection ---
    float _zuptBuf[ZUPT_WINDOW] = {};
    int   _zuptIdx   = 0;
    float _zuptSum   = 0;
    float _zuptSumSq = 0;

    // --- Motion lockout hysteresis ---
    int _motionLockout = 0;

    // Push sample into rolling window; return current variance
    float _pushZupt(float v) {
        float old = _zuptBuf[_zuptIdx];
        _zuptSum   += v   - old;
        _zuptSumSq += v*v - old*old;
        _zuptBuf[_zuptIdx] = v;
        _zuptIdx = (_zuptIdx + 1) & (ZUPT_WINDOW - 1);
        float mean = _zuptSum / ZUPT_WINDOW;
        return (_zuptSumSq / ZUPT_WINDOW) - mean * mean;  // E[x²] - E[x]²
    }

    // Current model bias at 'now' (micros)
    float _modelBias(unsigned long now) const {
        float dt = (now - _calEndTime) / 1e6f;
        return _biasA + _biasB * dt;
    }

public:
    void begin() {
        Wire.begin();
        Wire.setClock(400000);
        _sensor.begin(Wire, 1);
        _lastTime = micros();
    }

    void loadCalibration() {
        EEPROM.get(EEPROM_ADDR_A, _biasA);
        EEPROM.get(EEPROM_ADDR_B, _biasB);
        if (isnan(_biasA)) _biasA = 0;
        if (isnan(_biasB)) _biasB = 0;
        _calEndTime = micros();
    }

    void startCalibration(long samples) {
        _isCalibrating = true;
        _calCount = 0;
        _sumT = _sumT2 = _sumY = _sumTY = 0;
        _calStartTime = micros();
        _targetSamples = samples;
    }

    void update() {
        if (!_sensor.dataReady()) return;
        _sensor.getAGMT();

        float raw = _sensor.gyrZ();  // °/s

        if (_isCalibrating) {
            double t = (micros() - _calStartTime) / 1e6;
            _sumT  += t;
            _sumT2 += t * t;
            _sumY  += raw;
            _sumTY += t * raw;
            _calCount++;

            if (_calCount >= _targetSamples) {
                double n   = _calCount;
                double det = n * _sumT2 - _sumT * _sumT;

                if (abs(det) > 1e-12) {
                    _biasB = (float)((n * _sumTY - _sumT * _sumY) / det);
                    _biasA = (float)((_sumY - _biasB * _sumT) / n);
                } else {
                    _biasA = (float)(_sumY / n);
                    _biasB = 0;
                }

                _calEndTime    = micros();
                _isCalibrating = false;
                _lastTime      = _calEndTime;

                EEPROM.put(EEPROM_ADDR_A, _biasA);
                EEPROM.put(EEPROM_ADDR_B, _biasB);
            }

        } else {
            unsigned long now = micros();
            float dt = (now - _lastTime) / 1e6f;
            _lastTime = now;

            float corrected            = raw - _modelBias(now);
            float var                  = _pushZupt(raw);
            float rollingMeanRaw       = _zuptSum / ZUPT_WINDOW;
            float rollingMeanCorrected = rollingMeanRaw - _modelBias(now);

            _lastVar       = var;
            _lastCorrected = rollingMeanCorrected;

            // Extend lockout whenever motion is detected
            if (abs(rollingMeanCorrected) >= MOTION_THRESHOLD) {
                _motionLockout = MOTION_LOCKOUT_SAMPLES;
            }

            bool trulyStationary = (var < ZUPT_VAR_THRESHOLD)
                                && (abs(rollingMeanCorrected) < MOTION_THRESHOLD)
                                && (_motionLockout == 0);

            if (trulyStationary) {
                // Nudge biasA toward current raw to cancel residual drift
                float residual = raw - _modelBias(now);
                _biasA += ZUPT_ALPHA * residual;
            } else {
                _heading += corrected * dt;
                if (_motionLockout > 0) _motionLockout--;
            }
        }
    }

    float get_heading()       const { return _heading - _offset; }
    bool  is_calibrating()    const { return _isCalibrating; }
    void  reset()                   { _offset = _heading; }
    float get_biasA()         const { return _biasA; }
    float get_biasB()         const { return _biasB; }
    float get_lastVar()       const { return _lastVar; }
    float get_lastCorrected() const { return _lastCorrected; }
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
        } else {
            if (cmd == 'h') {
                Serial.println(gyro.get_heading());
            } else if (cmd == 'r') {
                gyro.reset();
            } else if (cmd == 'c') {
                long sampleCount = 100000;
                if (Serial.peek() >= '0' && Serial.peek() <= '9') {
                    sampleCount = Serial.parseInt();
                }
                gyro.startCalibration(sampleCount);
            } else if (cmd == 'i') {
                Serial.println("0");
            } else if (cmd == 'z') {
                Serial.println(gyro.get_biasA());
            } else if (cmd == 'v') {
                Serial.println(gyro.get_lastVar());
            } else if (cmd == 'l') {
                Serial.println(gyro.get_lastCorrected());
            }
        }
    }
}
