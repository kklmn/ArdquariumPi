// FILE: ardquarium.ino
// AUTHOR: Konstantin Klementiev
// VERSION: 1.0
// PURPOSE: measure various sensors and states to report to Raspberry Pi that runs ardquarium.py
// DATE: 9 Jan 2020
// URL:
// LICENSE MIT

#define oneWirePin 8
#define validTemperatureLo 15.  // same as in supply.temperatureOutlierLimits
#define validTemperatureHi 36.  // same as in supply.temperatureOutlierLimits
#define badTemperature validTemperatureHi+1 // must be outside of the valid range
#define flowRatePin 2  // check that this pin is usable for interrupts on your board; on Uno and Nano: 2 or 3
#define analogPin_pH A0
#define analogPin_EC A1
#define analogPin_TDS A2
#define mainsStatePin 9
// for BLE see http://www.martyncurrey.com/hm-10-bluetooth-4ble-modules/
#define BLERX 4  // from TX of HM-10
#define BLETX 5  // to RX of HM-10, must be divided from 5V to 3V3
#define BLEstatePin 11

#define portArduinoBaudRate 115200

#define UREF 5.00  // voltage for analogue sensors 

#define sampleInterval 200  // all in ms
#define reportInterval 5000  // don't put it too long: it would need more memory and may fail at the compilation
#define raspberryAliveWaitBeforeAlarm 100000 //  > raspberry boot time
#define mainsStateWaitBeforeAlarm 100000
#define alarmInterval 600000  // send next SMS not sooner than in 600 sec

#define arrayLength reportInterval / sampleInterval
unsigned long now, then;
int arrayIndex = 0, usedArrayLength = 0;
unsigned long lastSampleTime, lastReportTime, lastRaspberryAliveTime, lastMainsStateTime, lastAlarmTime;
int lastAlarm = 0;

// for 1Wire temperatures:
#include <DallasTemperature.h>  // by Miles Burton
#include <OneWire.h>  // by Jim Studt
DeviceAddress tempDeviceAddress;
OneWire oneWire(oneWirePin);
DallasTemperature sensors(&oneWire);
byte numberOf1WDevices;
# define MAXnumberOf1WDevices 4
float temperatureSamples[MAXnumberOf1WDevices][arrayLength]={0};
float temperatureAve[MAXnumberOf1WDevices];
float temperatureGlobal;

void setup_temperatures(void) {
  sensors.begin();
  delay(500);
  numberOf1WDevices = sensors.getDeviceCount();
  Serial.print("found ");
  Serial.print(numberOf1WDevices);
  Serial.print(" temperature device");
  if (numberOf1WDevices == 1)
    Serial.println();
  else
    Serial.println("s");
}

void get_temperatures(void) {
  float temp = 0;
  sensors.requestTemperatures();
  for (int iT=0; iT<numberOf1WDevices; iT++) {
    if (sensors.getAddress(tempDeviceAddress, iT)) {
      temp = sensors.getTempC(tempDeviceAddress);
    }
    temperatureSamples[iT][arrayIndex] = temp;
  }
}
// end for 1Wire temperatures:

// for flow rate counter
volatile int pulseCounter;
float flowRate;

void reset_counter() {
  pulseCounter = 0;
}

void _count() {  // ~30 cps
  pulseCounter++;
}

void setup_counter(void) {
  // we count when falling from HIGH, otherwise flowRatePin needs a pulldown resistor
  pinMode(flowRatePin, INPUT);
  digitalWrite(flowRatePin, HIGH);  # pullup is applied here
  then = millis();
  attachInterrupt(digitalPinToInterrupt(flowRatePin), _count, FALLING);
}

void get_flow_rate(void) {
  now = millis();
  if (now-then > 0) {
    float freq = float(pulseCounter) / (now-then) * 1000;  // Hz
    flowRate = freq / 5.5 * 60;  // L/h
  } else {
    flowRate = 0;
  }
  reset_counter();
  then = now;
}
// end for flow rate counter

// for analog pH
float volt_pH, val_pH;
float offset_pH = 7.0 - 6.93;  // as measured
int phArray[arrayLength]={0};
int phSum;

void get_analog_pH() {
  phArray[arrayIndex] = analogRead(analogPin_pH);
}

void get_val_pH() {
  val_pH = 3.5*volt_pH + offset_pH;  // https://wiki.dfrobot.com/PH_meter_SKU__SEN0161_
  
}
// end for analog pH

// for analog EC
#include <DFRobot_EC.h> // https://github.com/DFRobot/DFRobot_EC/archive/master.zip
DFRobot_EC ec;
float volt_EC, val_EC;
int ecArray[arrayLength]={0};
int ecSum;

void setup_analog_EC(void) {
  ec.begin();
}

void get_analog_EC() {
  ecArray[arrayIndex] = analogRead(analogPin_EC);
}

void get_val_EC() {
  // in µS/cm:
  val_EC = ec.readEC(volt_EC*1000, temperatureGlobal)*1000;  // https://wiki.dfrobot.com/Gravity__Analog_Electrical_Conductivity_Sensor___Meter_V2__K%3D1__SKU_DFR0300
}
// end for analog EC

// for analog TDS
float volt_TDS, val_TDS;
int tdsArray[arrayLength]={0};
int tdsSum;

void get_analog_TDS() {
  tdsArray[arrayIndex] = analogRead(analogPin_TDS);
}

void get_val_TDS() {
  // in ppm or mg/L:
  float compensationCoefficient = 1.0 + 0.02*(temperatureGlobal-25.0);
  float compensationVolatge = volt_TDS / compensationCoefficient;
  val_TDS = (133.42*compensationVolatge*compensationVolatge*compensationVolatge -
             255.86*compensationVolatge*compensationVolatge +
             857.39*compensationVolatge)*0.5;  // https://wiki.keyestudio.com/KS0429_keyestudio_TDS_Meter_V1.0
}
// end for analog TDS

// for mains state
int mainsState;

void get_mains_state() {
  mainsState = digitalRead(mainsStatePin);
}
// end for mains state

// for BLE
#include <SoftwareSerial.h>
SoftwareSerial BTserial(BLERX, BLETX);
int BLEstate;

void get_BLE_state() {
  BLEstate = digitalRead(BLEstatePin);
}
// end for BLE

// for LCD
#include <LiquidCrystal_PCF8574.h> // by Matthias Hertel
#include <Wire.h> 
LiquidCrystal_PCF8574 lcd(0x27); // address 0x27
char lcdmsg[5];
byte numBytes;

void setup_lcd() {
  Wire.begin();
  Wire.beginTransmission(0x27);
  int error = Wire.endTransmission();
  if (error == 0) {
    Serial.println("LCD found on 0x27");
    lcd.begin(16, 2);
    lcd.begin(20, 4);
    lcd.setBacklight(1);
  } else {
    Serial.println("no LCD found on 0x27");
  }
}

// two-line LCD
void print_to_lcd16x2() {
  lcd.setCursor(0, 0);
  // uncomment if needed in Fahrenheit:
  // temperatureGlobal = DallasTemperature::toFahrenheit(temperatureGlobal);
  dtostrf(temperatureGlobal, 4, 1, lcdmsg);
  lcd.print(lcdmsg);
  lcd.write(byte(223));  // degree sign
  lcd.print("C");

  lcd.print("");
  dtostrf(val_EC, 5, 0, lcdmsg);
  lcd.print(lcdmsg);
  lcd.write(byte(228));  // micro sign
  lcd.print("S/cm");

  lcd.setCursor(0, 1);
  dtostrf(flowRate, 4, 1, lcdmsg);
  lcd.print(lcdmsg);
  lcd.print("L/min");
  
  lcd.print("  pH");
  dtostrf(val_pH, 3, 1, lcdmsg);
  lcd.print(lcdmsg);
}

// four-line LCD
void print_to_lcd20x4() {
  float tempOut;

  lcd.setCursor(0, 0);
  for (int iT=0; iT<numberOf1WDevices; iT++) {
    tempOut = temperatureAve[iT];
    // uncomment if needed in Fahrenheit:
    // tempOut = DallasTemperature::toFahrenheit(tempOut);
    dtostrf(tempOut, 4, 1, lcdmsg);
    lcd.setCursor(iT*5, 0);
    lcd.print(lcdmsg);
  }  
  lcd.print("C");

  lcd.setCursor(0, 1);
  lcd.print("flow");
  dtostrf(flowRate, 4, 0, lcdmsg);
  lcd.print(lcdmsg);
  lcd.print("L/h");

  lcd.print("  pH");
  dtostrf(val_pH, 3, 1, lcdmsg);
  lcd.print(lcdmsg);

  lcd.setCursor(0, 2);
  lcd.print("EC");
  dtostrf(val_EC, 4, 0, lcdmsg);
  lcd.print(lcdmsg);
  lcd.write(byte(228));  // micro sign
  lcd.print("S/cm");

  lcd.print("  BLE ");
  if (BLEstate==1) lcd.print("on "); else lcd.print("off");

  lcd.setCursor(0, 3);
  lcd.print("TDS");
  dtostrf(val_TDS, 4, 0, lcdmsg);
  lcd.print(lcdmsg);
  lcd.print("ppm");

  lcd.print(" mains ");
  if (mainsState==1) lcd.print("on "); else lcd.print("off");
}
// end for LCD


void setup(void) {
  Serial.begin(portArduinoBaudRate);
  while (!Serial) ; // wait for Serial

  setup_lcd();
  setup_temperatures(); // oneWire
  setup_counter(); // flow rate
  setup_analog_EC();

  BTserial.begin(9600);  

  pinMode(mainsStatePin, INPUT);
  pinMode(BLEstatePin, INPUT);
  digitalWrite(mainsStatePin, LOW);
  digitalWrite(BLEstatePin, LOW);

  lastSampleTime = millis();
  lastReportTime = millis();
  lastRaspberryAliveTime = millis();
  lastMainsStateTime = millis();
  lastAlarmTime = millis();
}


void average_and_get_states() {
  float temperatureSumAll = 0;
  int numberOfValidTsAll = 0;
  for (int iT=0; iT<numberOf1WDevices; iT++) {
    float temperatureSum = 0;
    float numberOfValidTs = 0;
    for (int i=0; i<usedArrayLength; i++) {
      float temp = temperatureSamples[iT][i];
      if ((temp > validTemperatureLo) && (temp < validTemperatureHi)) {
        temperatureSum += temp;
        numberOfValidTs += 1;
      }
    }
    if (numberOfValidTs > 0) {
      temperatureAve[iT] = temperatureSum / numberOfValidTs;
    } else {
      temperatureAve[iT] = badTemperature; 
    }
    temperatureSumAll += temperatureSum;
    numberOfValidTsAll += numberOfValidTs;
  }
  if (numberOfValidTsAll > 0) {
    temperatureGlobal = temperatureSumAll / numberOfValidTsAll;
  } else {
    temperatureGlobal = badTemperature;
  }

  get_flow_rate();

  phSum = 0;
  for (int i=0; i<usedArrayLength; i++)
    phSum += phArray[i];
  volt_pH = float(phSum)/usedArrayLength * UREF/1024;
  get_val_pH();

  ecSum = 0;
  for (int i=0; i<usedArrayLength; i++)
    ecSum += ecArray[i];
  volt_EC = float(ecSum)/usedArrayLength * UREF/1024;
  get_val_EC();

  tdsSum = 0;
  for (int i=0; i<usedArrayLength; i++)
    tdsSum += tdsArray[i];
  volt_TDS = float(tdsSum)/usedArrayLength * UREF/1024;
  get_val_TDS();

  get_mains_state();

  get_BLE_state();
}


void check_alarms(void) {
  String buf;
  lastAlarm = 0;
  now = millis();

  numBytes = Serial.available();
  if (numBytes > 0) {
    buf = Serial.readString();
  } else {
    buf = " ";
  }
  if (buf.startsWith("alive")) {
    lastRaspberryAliveTime = now;
  } else if (buf.startsWith("SMS")) {
    BTserial.write("SMS:test");
  } else {
    if ((now - lastRaspberryAliveTime) >= raspberryAliveWaitBeforeAlarm)
      lastAlarm = lastAlarm | 1;
  }

  if (mainsState == 1) {
    lastMainsStateTime = now;
  } else {
    if ((now - lastMainsStateTime) >= mainsStateWaitBeforeAlarm)
      lastAlarm = lastAlarm | 2;
  }
}


void report_results(void) {
  now = millis();

// comment out when testing
  if (lastAlarm & 1) {  // no raspberry
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("RPi disconnected");
    lcd.setCursor(0, 1);
    if ((now - lastAlarmTime) >= alarmInterval) {
      lastAlarmTime = now;
      if (BLEstate == 1) {
        BTserial.write("SMS:noRPi");
        lcd.print("SMS sent");
      }
    } else {
      dtostrf((now - lastRaspberryAliveTime) / 1000, 5, 0, lcdmsg);
      lcd.print(lcdmsg);
      lcd.print(" sec");
    }
  }
// end comment out when testing

  if ((lastAlarm & 2) && (BLEstate == 1)) {  // no mains
    if ((now - lastAlarmTime) >= alarmInterval) {
      lastAlarmTime = now;
      BTserial.write("SMS:noMains");
    }
  }

  for (int iT=0; iT<numberOf1WDevices; iT++) {
    Serial.print(temperatureAve[iT], 3);
    Serial.print("\t");
  }
  Serial.print(flowRate, 2);
  Serial.print("\t");

  Serial.print(val_pH, 4);
  Serial.print("\t");

  Serial.print(val_EC, 2);
  Serial.print("\t");

  Serial.print(val_TDS, 2);
  Serial.print("\t");

  Serial.print(mainsState);
  Serial.print("\t");

  Serial.print(BLEstate);
  Serial.println();

// comment out when testing
  if (lastAlarm & 1)  // no raspberry
    return;
// end comment out when testing

//  print_to_lcd16x2();
  print_to_lcd20x4();
}


void loop(void) {
  now = millis();
  if ((now - lastSampleTime) >= sampleInterval) {
    get_temperatures();
    get_analog_pH();
    get_analog_EC();
    get_analog_TDS();

    lastSampleTime = now;
    arrayIndex++;
    if (arrayIndex == arrayLength) arrayIndex = 0;
    if (usedArrayLength < arrayLength) usedArrayLength++;
  }

  if ((now - lastReportTime) >= reportInterval) {
    average_and_get_states();
    check_alarms();
    report_results();
    lastReportTime = now;
  }
}
