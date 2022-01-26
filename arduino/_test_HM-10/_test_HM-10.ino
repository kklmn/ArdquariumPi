#define portArduinoBaudRate 115200

#include <SoftwareSerial.h>
#define BLERX 4  // from TX of HM-10
#define BLETX 5  // to RX of HM-10, must be divided from 5V to 3V3
#define BLEBaudRate 9600
#define waitWriteBLE 0
SoftwareSerial BTserial(BLERX, BLETX);

char c=' ';
boolean NL = true;
 
void setup() 
{
    Serial.begin(portArduinoBaudRate);
    Serial.print("Sketch:   ");   Serial.println(__FILE__);
    Serial.print("Uploaded: ");   Serial.println(__DATE__);
    Serial.println(" ");
 
    BTserial.begin(BLEBaudRate);
    Serial.print("BTserial started at ");
    Serial.println(BLEBaudRate);
}
 
void loop()
{
    // Read from the Bluetooth module and send to the Arduino Serial Monitor
    if (BTserial.available())
    {
        c = BTserial.read();
        Serial.write(c);
    }
 
 
    // Read from the Serial Monitor and send to the Bluetooth module
    if (Serial.available())
    {
        c = Serial.read();
 
        // do not send line end characters to the HM-10
        if (c!=10 & c!=13 ) 
        {  
             BTserial.write(c);
             delay(waitWriteBLE);
        }
 
        // Echo the user input to the main window. 
        // If there is a new line print the ">" character.
        if (NL) { Serial.print("\r\n>");  NL = false; }
        Serial.write(c);
        if (c==10) { NL = true; }
    }
}
