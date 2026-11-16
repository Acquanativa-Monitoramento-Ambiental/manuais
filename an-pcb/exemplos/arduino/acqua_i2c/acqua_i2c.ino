/*
 * acqua_i2c.ino — terminal serial para os módulos I²C Acquanativa
 * (ACQUA-OD, ACQUA-pH e ACQUA-ORP, placas AN-PCB, firmware 1.1).
 *
 * Use para conferir a ligação, ler, calibrar e mudar o endereço sem escrever
 * código: digite o comando no Monitor Serial (9600 baud, "Nova linha") e veja
 * a resposta do módulo.
 *
 * Ligação (Arduino Uno, 5 V):
 *   J1 pino 1 VCC -> 5V      J1 pino 2 SCL -> A5 (SCL)
 *   J1 pino 3 SDA -> A4 (SDA) J1 pino 4 GND -> GND
 * Pull-ups de 4,7 kΩ de SDA e SCL ao VCC são recomendados.
 * Com ESP32 ou outro mestre de 3,3 V, alimente o ACQUA-OD e o ACQUA-pH com
 * 3,3 V. O ACQUA-ORP precisa de 5 V: use um conversor de nível de I²C.
 *
 * Comandos do terminal (além dos comandos do módulo, ver o manual):
 *   ?        procura módulos no barramento (endereços 8 a 119)
 *   @<n>     passa a falar com o módulo no endereço n (decimal). Ex.: @64
 *   ler      lê o módulo atual a cada segundo; envie qualquer tecla para parar
 *
 * Endereços de fábrica: ACQUA-OD 32, ACQUA-pH 64, ACQUA-ORP 96.
 */
#include <Wire.h>

uint8_t endereco = 32;  // ACQUA-OD; troque com @<n>

// Envia um comando e devolve a resposta ("" se o módulo não respondeu).
String enviar(uint8_t addr, const char *comando) {
  Wire.beginTransmission(addr);
  Wire.write(comando);
  if (Wire.endTransmission() != 0) return "";

  delay(450);  // o módulo precisa de 450 ms para processar

  String resposta = "";
  Wire.requestFrom(addr, (uint8_t)32);
  while (Wire.available()) {
    char c = Wire.read();
    if (c == '\0') break;  // fim da resposta
    resposta += c;
  }
  while (Wire.available()) Wire.read();
  return resposta;
}

void procurar() {
  Serial.println(F("Procurando módulos..."));
  int achados = 0;
  for (uint8_t a = 8; a <= 119; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      String info = enviar(a, "Info");  // ex.: pH,EZO,1.1
      Serial.print(F("  endereço "));
      Serial.print(a);
      Serial.print(F(": "));
      Serial.println(info.length() ? info : String(F("(não respondeu ao Info)")));
      achados++;
    }
  }
  if (!achados) Serial.println(F("  nenhum. Confira VCC, GND, SDA, SCL e os pull-ups."));
}

void lerContinuo() {
  Serial.println(F("Lendo a cada segundo. Envie qualquer tecla para parar."));
  while (Serial.available()) Serial.read();
  while (!Serial.available()) {
    Serial.println(enviar(endereco, "R"));
    delay(550);  // + 450 ms dentro de enviar() = 1 leitura por segundo
  }
  while (Serial.available()) Serial.read();
}

void setup() {
  Serial.begin(9600);
  Wire.begin();
  Wire.setClock(100000);
  delay(500);
  Serial.println(F("Terminal I2C Acquanativa. Comandos: ?  @<endereço>  ler"));
  procurar();
  Serial.print(F("Módulo atual: "));
  Serial.println(endereco);
}

void loop() {
  if (!Serial.available()) return;

  String linha = Serial.readStringUntil('\n');
  linha.trim();
  if (linha.length() == 0 || linha.length() > 31) return;

  if (linha == "?") {
    procurar();
  } else if (linha.startsWith("@")) {
    int n = linha.substring(1).toInt();
    if (n >= 8 && n <= 119) {
      endereco = n;
      Serial.print(F("Módulo atual: "));
      Serial.println(endereco);
    } else {
      Serial.println(F("Endereço de 8 a 119."));
    }
  } else if (linha.equalsIgnoreCase("ler")) {
    lerContinuo();
  } else {
    Serial.print(F("> "));
    Serial.println(linha);
    String r = enviar(endereco, linha.c_str());
    Serial.println(r.length() ? r : String(F("(sem resposta: endereço errado ou módulo desligado)")));

    // Depois de I2C,<n> o módulo já responde no endereço novo.
    String l = linha;
    l.toLowerCase();
    if (l.startsWith("i2c,") && l != "i2c,?") {
      int n = l.substring(4).toInt();
      if (n >= 8 && n <= 119) {
        endereco = n;
        Serial.println(enviar(endereco, "I2C,?"));
      }
    }
  }
}
