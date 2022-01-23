#define leakPin A0

void setup() {
  // initialize serial communication:
  Serial.begin(115200);
}

// the loop routine runs over and over again forever:
void loop() {
  // read the input on analog pin 0:
  int sensorValue = analogRead(leakPin);
  Serial.println(sensorValue);
  delay(500);
}
