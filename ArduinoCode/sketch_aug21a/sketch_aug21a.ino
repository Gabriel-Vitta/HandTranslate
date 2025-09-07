#include <LiquidCrystal.h>

// Pinos do LCD: RS, E, D4, D5, D6, D7
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

void setup() {
  lcd.begin(16, 2);           // Inicializa LCD 16x2
  Serial.begin(9600);         // Inicializa comunicação serial
  lcd.print("Aguardando...");
}

void loop() {
  if (Serial.available() > 0) {
    char comando = Serial.read();

    lcd.clear(); // Limpa a tela para nova mensagem

    switch (comando) {
      case 'J':
        lcd.print("JOINHA 👍");
        break;

      case 'D':
        lcd.print("DESGOSTEI 👎");
        break;

      case 'E':
        lcd.print("ESPERE ✋");
        break;

      case 'L':
        lcd.print("Letra L 🤟");
        break;

      default:
        lcd.print("Comando invalido");
        break;
    }

    delay(2000); // Mostra a mensagem por 2 segundos
    lcd.clear();
    lcd.print("Aguardando...");
  }
}
