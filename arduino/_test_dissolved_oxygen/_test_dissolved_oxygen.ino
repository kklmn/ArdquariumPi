#define oneWirePin 8
#define analogPin_DO A2
#define validTemperatureLo 0.
#define validTemperatureHi 41.
#define badTemperature 55

#define portArduinoBaudRate 115200
#define UREF 5.00  // voltage for analogue sensors 
#define ADCRES 1024  // ADC Resolution

#define sampleInterval 200  // all in ms
#define reportInterval 5000  // don't make it too long: it would need more memory and may fail at the compilation

#define arrayLength reportInterval / sampleInterval
unsigned long now, then;
int arrayIndex = 0, usedArrayLength = 0;
unsigned long lastSampleTime, lastReportTime;

#include <DallasTemperature.h>  // by Miles Burton
#include <OneWire.h>  // by Jim Studt
DeviceAddress tempDeviceAddress;
OneWire oneWire(oneWirePin);
DallasTemperature sensors(&oneWire);
byte numberOf1WDevices;
# define MAXnumberOf1WDevices 4
float temperatureSamples[MAXnumberOf1WDevices][arrayLength] = {0};
float temperatureAve[MAXnumberOf1WDevices];
float temperatureGlobal;

// for 1Wire temperatures:
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
  for (int iT = 0; iT < numberOf1WDevices; iT++) {
    if (sensors.getAddress(tempDeviceAddress, iT)) {
      temp = sensors.getTempC(tempDeviceAddress);
    }
    temperatureSamples[iT][arrayIndex] = temp;
  }
}
// end for 1Wire temperatures:


// for analog DO
float volt_DO, val_DO;
int doArray[arrayLength] = {0};
int doSum;
#define DO_CAL_T1 27.6 //C
#define DO_CAL_V1 0.36 //V
//#define DO_CAL_K (DO_CAL_V1-DO_CAL_V2) / (DO_CAL_T1-DO_CAL_T2) // = (V1-V2)/(T1-T2)
#define DO_CAL_K 0.035 // = (V1-V2)/(T1-T2)

void get_analog_DO() {
  doArray[arrayIndex] = analogRead(analogPin_DO);
}

void get_val_DO() {
  float VSat = (temperatureGlobal-DO_CAL_T1) * DO_CAL_K + DO_CAL_V1;
  val_DO = volt_DO / VSat * (
    -0.00005724376*temperatureGlobal*temperatureGlobal*temperatureGlobal
    +0.0069162346*temperatureGlobal*temperatureGlobal
    -0.38819795*temperatureGlobal + 14.52872);  // my fit of
    // https://wiki.dfrobot.com/Gravity__Analog_Dissolved_Oxygen_Sensor_SKU_SEN0237
}
// end for analog DO

void setup(void) {
  Serial.begin(portArduinoBaudRate);
  while (!Serial) ; // wait for Serial

  setup_temperatures(); // oneWire

  lastSampleTime = millis();
  lastReportTime = millis();
}

void average() {
  float temperatureSumAll = 0;
  int numberOfValidTsAll = 0;
  for (int iT = 0; iT < numberOf1WDevices; iT++) {
    float temperatureSum = 0;
    float numberOfValidTs = 0;
    for (int i = 0; i < usedArrayLength; i++) {
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

  doSum = 0;
  for (int i = 0; i < usedArrayLength; i++)
    doSum += doArray[i];
  volt_DO = float(doSum) / usedArrayLength * UREF / ADCRES;
  get_val_DO();
}

void report_results(void) {
  now = millis();

  for (int iT = 0; iT < numberOf1WDevices; iT++) {
    Serial.print("T=");
    Serial.print(temperatureAve[iT], 3);
    Serial.print("C\t");
  }
  Serial.print("Vout(DO)=");
  Serial.print(volt_DO, 4);
  Serial.print(" V\t");
  Serial.print("DO=");
  Serial.print(val_DO, 2);
  Serial.println("mg/L");
}

void loop(void) {
  now = millis();
  if ((now - lastSampleTime) >= sampleInterval) {
    get_temperatures();
    get_analog_DO();

    lastSampleTime = now;
    arrayIndex++;
    if (arrayIndex == arrayLength) arrayIndex = 0;
    if (usedArrayLength < arrayLength) usedArrayLength++;
  }

  if ((now - lastReportTime) >= reportInterval) {
    average();
    report_results();
    lastReportTime = now;
  }
}
