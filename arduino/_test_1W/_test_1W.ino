#define oneWirePin 8

#include <DallasTemperature.h>  // by Miles Burton
#include <OneWire.h>  // by Jim Studt
DeviceAddress tempDeviceAddress;
OneWire oneWire(oneWirePin);
DallasTemperature sensors(&oneWire);
byte numberOf1WDevices;

void setup_temperatures(void) {
  pinMode(oneWirePin, INPUT_PULLUP);
  sensors.begin();
  numberOf1WDevices = sensors.getDeviceCount();
  Serial.print("found ");
  Serial.print(numberOf1WDevices);
  Serial.print(" temperature device");
  if (numberOf1WDevices > 1)
    Serial.println("s");
  else
    Serial.println();
}

void get_temperatures(void) {
  float temp = 0;
  sensors.requestTemperatures();
  for (int iT = 0; iT < numberOf1WDevices; iT++) {
    if (sensors.getAddress(tempDeviceAddress, iT)) {
      temp = sensors.getTempC(tempDeviceAddress);
      Serial.print(temp);
      Serial.print(' ');
    }
  }
  Serial.println();
}
// end for 1Wire temperatures:


void setup(void) {
  Serial.begin(115200);
  while (!Serial)  // wait for Serial
    ;
  setup_temperatures(); // oneWire
}

void loop(void) {
  get_temperatures();
  delay(500);
}
