#include <TimerOne.h>

#define flowRatePin 2  // check that this pin is usable for interrupts on your board; on Uno and Nano: 2 and 3
#define testPin 10 // 9 or 10

#define reportInterval 5000

volatile int pulseCounter = 0;
float flowRate;
unsigned long now, then, dt;
unsigned long lastReportTime;

void reset_counter()
{
  pulseCounter = 0;
}

void _count()
{
  pulseCounter++;
//  Serial.println(pulseCounter);
}

void get_flow_rate(void) {
  now = millis();
  dt = now - then;
  if (dt > 0) {
    float freq = float(pulseCounter) / dt * 1000;  // Hz
    flowRate = freq / 5.5;  // L/min
  } else {
    flowRate = 0;
  }
  reset_counter();
  then = now;
}

void setup()
{
  Serial.begin(115200);

  pinMode(testPin, OUTPUT);
  Timer1.initialize(50000);  // Frequency, 50000us = 20Hz
  Timer1.pwm(testPin, 512);  // 50% duty cycle on pin 9

  // we count when falling from HIGH, otherwise flowRatePin needs a pulldown resistor
  pinMode(flowRatePin, INPUT);
  digitalWrite(flowRatePin, HIGH);  # pullup is applied here
  attachInterrupt(digitalPinToInterrupt(flowRatePin), _count, FALLING);
  then = millis();
}

void loop()
{
  now = millis();
  if ((now - lastReportTime) >= reportInterval) {
    get_flow_rate();
    Serial.print(flowRate, 3);
    Serial.print("\t");
    Serial.print(pulseCounter);
    Serial.print("\t");
    Serial.print(dt);
    Serial.println();
    lastReportTime = now;
  }
}
