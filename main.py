from machine import Pin, UART
import time
from ble_peripheral import BLESimplePeripheral
from config import RELAY_MOEDA_PIN,RELAY_NOTA_PIN, MOEDA_PIN, NOTA_PIN

# === UART Impressora ===
printer_uart = UART(2, baudrate=9600, tx=Pin(17), rx=Pin(16))

# === BLE ===
ble_peripheral = BLESimplePeripheral(name="Arduino_BLE")

# === Relé (Moedeiro) ===
# === Relés ===
rele_moeda = Pin(RELAY_MOEDA_PIN, Pin.OUT)
rele_moeda.off()

rele_nota = Pin(RELAY_NOTA_PIN, Pin.OUT)
rele_nota.off()


# === Moedeiro (Pulso) ===
moeda_pin = Pin(MOEDA_PIN, Pin.IN, Pin.PULL_UP)
moeda_count = 0
last_moeda_time = time.ticks_ms()
moeda_timeout = 300  # ms
moeda_estado_anterior = moeda_pin.value()

# === Noteiro (BV30 - Pulso) ===
nota_pin = Pin(NOTA_PIN, Pin.IN, Pin.PULL_UP)
nota_count = 0
last_nota_time = time.ticks_ms()
nota_timeout = 500  # ms

# === Impressora ===
def check_printer_status():
    printer_uart.write(b'\x10\x04\x14')  # ESC/POS status
    time.sleep(0.1)
    if printer_uart.any():
        status = printer_uart.read()
        if status:
            byte = status[0]
            return "SEM_PAPEL" if (byte & 0x20) else "OK"
    return "ERRO"

def imprimir_talao(conteudo):
    printer_uart.write(b'\x1B\x40')  # Reset
    printer_uart.write(conteudo.encode("utf-8"))
    printer_uart.write(b'\n\n\n')
    printer_uart.write(b'\x1D\x56\x42\x10')  # Cut

# === BLE Handler ===
def handle_ble_command(data):
    try:
        comando = data.decode().strip()
    except:
        print("❌ Erro ao decodificar comando BLE")
        return

    print("📩 BLE recebido:", comando)

    if comando == "MOEDA|ON":
        rele_moeda.on()
        ble_peripheral.send("OK")
        print("✅ Moedeiro ativado")

    elif comando == "MOEDA|OFF":
        rele_moeda.off()
        ble_peripheral.send("OK")
        print("✅ Moedeiro desativado")

    elif comando == "NOTA|ON":
        rele_nota.on()
        ble_peripheral.send("OK")
        print("✅ Noteiro ativado")

    elif comando == "NOTA|OFF":
        rele_nota.off()
        ble_peripheral.send("OK")
        print("✅ Noteiro desativado")

    elif comando == "STATUS|PRINTER":
        estado = check_printer_status()
        ble_peripheral.send(estado)
        print("📄 Estado da impressora:", estado)

    elif comando.startswith("TALAO|PRINT|"):
        conteudo = comando.split("|", 2)[-1]
        imprimir_talao(conteudo)
        estado = check_printer_status()
        ble_peripheral.send(estado if estado != "OK" else "OK")
        print("🧾 Talão impresso. Estado:", estado)


# === BLE Init ===
ble_peripheral.on_write(handle_ble_command)

# === LOOP PRINCIPAL ===
while True:
    now = time.ticks_ms()

    # === Leitura de MOEDA ===
    estado_atual = moeda_pin.value()
    if estado_atual == 0 and moeda_estado_anterior == 1:
        if time.ticks_diff(now, last_moeda_time) > moeda_timeout:
            moeda_count += 1
            print(f"🪙 Moeda detectada: {moeda_count}")
            ble_peripheral.send(f"MOEDA|{moeda_count}")
            last_moeda_time = now
    moeda_estado_anterior = estado_atual

    # === Leitura de NOTA ===
    if nota_pin.value() == 0:
        if time.ticks_diff(now, last_nota_time) > 50:
            nota_count += 1
            last_nota_time = now
            print(f"📟 Pulso de nota detectado: {nota_count}")
        while nota_pin.value() == 0:
            pass  # Espera subir

    if nota_count > 0 and time.ticks_diff(now, last_nota_time) > nota_timeout:
        print(f"💶 Nota inserida: +{nota_count}€")
        ble_peripheral.send(f"NOTA|{nota_count}")
        nota_count = 0

    time.sleep(0.005)
