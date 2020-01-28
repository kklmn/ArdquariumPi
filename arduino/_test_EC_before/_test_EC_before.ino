// https://wiki.dfrobot.com/Gravity__Analog_Electrical_Conductivity_Sensor___Meter_V2__K%3D1__SKU_DFR0300
#include <EEPROM.h>
#define KVALUEADDR 0x0A

void setup(){
  for(byte i = 0;i< 8; i++ ){
    EEPROM.write(KVALUEADDR+i, 0xFF);
  }
}

void loop(){
}
