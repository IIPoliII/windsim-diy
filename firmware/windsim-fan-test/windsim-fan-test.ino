// Wind sim DIY - test des ventilateurs (Arduino Uno)
// PWM 25 kHz sur D9 (gauche) et D10 (droite), Timer1 en phase correcte.
// Cycle : 0 % -> 30 % -> 60 % -> 100 %, 4 s par palier.
// A flasher AVANT le firmware SimHub pour verifier le cablage.

const uint16_t TOP = 320;               // 16 MHz / (2 * 320) = 25 kHz

void setDuty(uint8_t pin, uint8_t pct) {
  uint16_t v = (uint32_t)pct * TOP / 100;
  if (pin == 9)  OCR1A = v;
  if (pin == 10) OCR1B = v;
}

void setup() {
  pinMode(9, OUTPUT);
  pinMode(10, OUTPUT);
  TCCR1A = 0; TCCR1B = 0; TCNT1 = 0;
  TCCR1A = _BV(COM1A1) | _BV(COM1B1) | _BV(WGM11); // mode 10 : phase correcte, TOP = ICR1
  TCCR1B = _BV(WGM13) | _BV(CS10);                 // pas de prediviseur
  ICR1 = TOP;
  setDuty(9, 0);
  setDuty(10, 0);
  Serial.begin(115200);
}

void loop() {
  const uint8_t steps[] = {0, 30, 60, 100};
  for (uint8_t i = 0; i < 4; i++) {
    setDuty(9, steps[i]);
    setDuty(10, steps[i]);
    Serial.print("PWM ");
    Serial.print(steps[i]);
    Serial.println(" %");
    delay(4000);
  }
}
