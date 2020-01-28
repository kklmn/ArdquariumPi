#include <Wire.h> 
#include <LiquidCrystal_PCF8574.h> // by Matthias Hertel

LiquidCrystal_PCF8574 lcd(0x27); // address 0x27
char lcdmsg[5];
int error;

void setup()
{
  Serial.begin(9600);
  // wait for Serial
  while (!Serial)
    ;
  Wire.begin();
  Wire.beginTransmission(0x27);
  error = Wire.endTransmission();
  if (error == 0) {
    Serial.println("LCD found on 0x27");
    lcd.begin(16, 2);
    lcd.setBacklight(1);
  } else {
    Serial.println("no LCD found on 0x27");
  }

  lcd.print("4T=");
  dtostrf(25.24, 4, 1, lcdmsg);
  lcd.print(lcdmsg);
  lcd.write(0xDF); // degree sign
  lcd.print("C");
}

void loop()
{
  // Do nothing here...
}
