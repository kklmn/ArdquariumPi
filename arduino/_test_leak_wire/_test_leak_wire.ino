#define leakStatePin 12

void setup() {
  // initialize serial communication:
  Serial.begin(115200);
  pinMode(leakStatePin, INPUT_PULLUP);
}

void loop() {
  int leakVal = digitalRead(leakStatePin);

  Serial.print(leakVal);
  Serial.println();

  if (leakVal == HIGH) {
    digitalWrite(13, LOW);
  } else {
    digitalWrite(13, HIGH);
  }

  delay(1000);
}
