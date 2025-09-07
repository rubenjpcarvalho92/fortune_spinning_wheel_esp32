import bluetooth
import struct

# === Pinos de configuração do hardware ===

# GPIO que ativa o relé do moedeiro
RELAY_MOEDA_PIN = 21     # novo pino (em vez do queimado 18)

# GPIO que ativa o relé da nota de 10€
RELAY_NOTA_10_PIN = 19

# GPIO que ativa o relé da nota de 5€
RELAY_NOTA_5_PIN = 18     # usa um pino livre (verifica se 18 já foi substituído)

# GPIO onde chegam os pulsos do moedeiro
MOEDA_PIN = 15

# GPIO onde chegam os pulsos do noteiro (BV30)
NOTA_PIN = 23

# GPIOs para UART da impressora térmica
PRINTER_TX = 16
PRINTER_RX = 17

POWER_ON = 13


def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None):
    payload = bytearray()

    def _append(ad_type, value):
        payload.extend(struct.pack("BB", len(value) + 1, ad_type) + value)

    if name:
        _append(0x09, name.encode())

    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(0x02, b)
            elif len(b) == 16:
                _append(0x06, b)

    return payload
