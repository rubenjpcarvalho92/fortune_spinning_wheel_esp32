import bluetooth
import struct
from micropython import const

# === advertising_payload BLE ===
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

# === Classe BLE UART ===
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

class BLESimplePeripheral:
    def __init__(self, name="ESP32"):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._connections = set()
        self._callback = None

        UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
        UART_TX = (bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"), bluetooth.FLAG_NOTIFY)
        UART_RX = (bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"), bluetooth.FLAG_WRITE)

        UART_SERVICE = (UART_UUID, (UART_TX, UART_RX))
        ((self._tx_handle, self._rx_handle),) = self._ble.gatts_register_services((UART_SERVICE,))

        self._advertise(name)

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print("🔗 BLE conectado")

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)
            print("❌ BLE desconectado")
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if value_handle == self._rx_handle and self._callback:
                value = self._ble.gatts_read(self._rx_handle)
                self._callback(value)

    def on_write(self, callback):
        self._callback = callback

    def send(self, data):
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._tx_handle, data)

    def _advertise(self, name="ESP32"):
        adv_data = advertising_payload(name=name)
        self._ble.gap_advertise(100, adv_data)
