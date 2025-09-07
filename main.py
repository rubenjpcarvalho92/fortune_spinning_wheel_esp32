from machine import Pin, UART
import time
from ble_peripheral import BLESimplePeripheral
from config import RELAY_MOEDA_PIN, RELAY_NOTA_10_PIN, RELAY_NOTA_5_PIN, MOEDA_PIN, NOTA_PIN, POWER_ON, RELAY_POWER_ON

# === UART Impressora ===
printer_uart = UART(2, baudrate=115200, tx=Pin(17), rx=Pin(16))

# === BLE ===
ble_peripheral = BLESimplePeripheral(name="Arduino_BLE")

# === Relés ===
rele_moeda = Pin(RELAY_MOEDA_PIN, Pin.OUT)
rele_nota_10 = Pin(RELAY_NOTA_10_PIN, Pin.OUT)  # ✅ nome correto
rele_nota_5 = Pin(RELAY_NOTA_5_PIN, Pin.OUT)
rele_moeda.off()
rele_nota_10.off()
rele_nota_5.off()

# === Moedeiro (Pulso) ===
moeda_pin = Pin(MOEDA_PIN, Pin.IN, Pin.PULL_UP)
moeda_count = 0
last_moeda_time = time.ticks_ms()
moeda_timeout = 300
moeda_estado_anterior = moeda_pin.value()

# === Noteiro (Pulso por grupo) ===
nota_pin = Pin(NOTA_PIN, Pin.IN, Pin.PULL_UP)
nota_pulsos = 0
pulso_em_andamento = False
inicio_pulso = 0
ultimo_pulso = 0
NOTA_PULSO_MIN_MS = 60
NOTA_PULSO_TIMEOUT_MS = 250

# === BLE buffer ===
ble_buffer = ""

# === Impressora ===
def check_printer_status():
    printer_uart.write(b'\x10\x04\x14')
    time.sleep(0.1)
    if printer_uart.any():
        status = printer_uart.read()
        if status:
            byte = status[0]
            return "SEM_PAPEL" if (byte & 0x20) else "OK"
    return "ERRO"

def imprimir_talao_jogo(numero_talao, premios_raw):
    premios = premios_raw.split(":")
    printer_uart.write(b'\x1B\x40')
    printer_uart.write(b'\x1B\x61\x01')
    printer_uart.write(b'\x1D\x21\x00')
    printer_uart.write(b'\x1B\x45\x00')
    printer_uart.write("\n--- TALAO DE JOGO ---\n".encode("utf-8"))
    printer_uart.write(f"{numero_talao}\n\n".encode("utf-8"))
    for premio in premios:
        printer_uart.write(b'\x1B\x21\x30')
        printer_uart.write(b'\x1B\x45\x01')
        printer_uart.write(f"{premio}\n".encode("utf-8"))
        printer_uart.write(b'\n')
        printer_uart.write(b'\x1B\x21\x00')
        printer_uart.write(b'\x1B\x45\x00')
    printer_uart.write(b'\x1D\x21\x00')
    printer_uart.write(b'\x1B\x45\x00')
    printer_uart.write("\nObrigado por jogar!\n".encode("utf-8"))
    printer_uart.write(b'\x1B\x61\x00')
    printer_uart.write(b'\n\n\n')
    printer_uart.write(b'\x1D\x56\x42\x10')

# === BLE Handler ===
def handle_ble_command(data):
    global ble_buffer, moeda_count, nota_pulsos
    try:
        fragmento = data.decode()
        ble_buffer += fragmento
    except:
        print("❌ Erro ao decodificar fragmento BLE")
        return

    print("📩 Fragmento recebido:", repr(fragmento))

    if ble_buffer.endswith("!"):
        comando = ble_buffer[:-1]
        ble_buffer = ""
        print("✅ Comando completo:", comando)

        try:
            if comando == "MOEDA|ON":
                rele_moeda.on()
                moeda_count = 0
                ble_peripheral.send("OK")
                print("✅ Moedeiro ativado")

            elif comando == "MOEDA|OFF":
                rele_moeda.off()
                ble_peripheral.send("OK")
                print("✅ Moedeiro desativado")

            elif comando == "NOTEIRO|ON":
                rele_nota_10.on()
                rele_nota_5.on()
                nota_pulsos = 0
                ble_peripheral.send("OK")
                print("✅ Noteiro ativado")

            elif comando == "NOTEIRO|OFF|10":
                rele_nota_10.off()
                ble_peripheral.send("OK")
                print("✅ Noteiro 10€ desativado")

            elif comando == "NOTEIRO|OFF|5":
                rele_nota_5.off()
                ble_peripheral.send("OK")
                print("✅ Noteiro 5€ desativado")

            elif comando == "STATUS|PRINTER":
                estado = check_printer_status()
                ble_peripheral.send(estado)
                print("📄 Estado da impressora:", estado)
                
            elif comando == "DINHEIRO|ON":
                rele_moeda.on()
                rele_nota_10.on()
                rele_nota_5.on()
                moeda_count = 0
                nota_pulsos = 0
                ble_peripheral.send("OK")
                print("✅ Moedeiro e noteiro ativados")

            elif comando == "DINHEIRO|OFF":
                rele_moeda.off()
                rele_nota_10.off()
                rele_nota_5.off()
                ble_peripheral.send("OK")
                print("✅ Moedeiro e noteiro desativados")


            elif comando.startswith("TALAO|PRINT|"):
                partes = comando.split("|", 3)
                if len(partes) != 4:
                    raise ValueError("Comando TALAO|PRINT| malformado.")
                _, _, numero_talao, premios_raw = partes
                imprimir_talao_jogo(numero_talao, premios_raw)
                estado = check_printer_status()
                ble_peripheral.send("OK")
                print("📤 Estado enviado para app (forçado OK):", estado)

        except Exception as e:
            print("❌ Erro ao processar comando:", str(e))
            ble_peripheral.send("ERRO")

# === BLE Init ===
ble_peripheral.on_write(handle_ble_command)

# === LOOP PRINCIPAL ===
while True:
    now = time.ticks_ms()

    # Moedeiro
    estado_atual = moeda_pin.value()
    if estado_atual == 0 and moeda_estado_anterior == 1:
        if time.ticks_diff(now, last_moeda_time) > 60:
            moeda_count += 1
            last_moeda_time = now
    elif moeda_count > 0 and time.ticks_diff(now, last_moeda_time) > 1000:
        if moeda_count == 1:
            print("🪙 Moeda de 1€ detectada")
            ble_peripheral.send("MOEDA|1")
        elif moeda_count == 4:
            print("🪙 Moeda de 2€ detectada")
            ble_peripheral.send("MOEDA|2")
        else:
            print(f"⚠️ Pulsos inválidos ignorados: {moeda_count}")
        moeda_count = 0
    moeda_estado_anterior = estado_atual

    # Noteiro
    if nota_pin.value() == 0:
        if not pulso_em_andamento:
            inicio_pulso = now
            pulso_em_andamento = True
        ultimo_pulso = now
    elif pulso_em_andamento and time.ticks_diff(now, ultimo_pulso) > NOTA_PULSO_MIN_MS:
        pulso_em_andamento = False
        nota_pulsos += 1
        print(f"📟 Pulso nota detectado: {nota_pulsos}")

    if nota_pulsos > 0 and time.ticks_diff(now, ultimo_pulso) > NOTA_PULSO_TIMEOUT_MS:
        if nota_pulsos == 5:
            print("💶 Nota de 5€ detectada")
            ble_peripheral.send("NOTA|5")
        elif nota_pulsos == 10:
            print("💶 Nota de 10€ detectada")
            ble_peripheral.send("NOTA|10")
        else:
            print(f"⚠️ Pulsos inválidos ignorados: {nota_pulsos}")
        nota_pulsos = 0

    time.sleep(0.005)
