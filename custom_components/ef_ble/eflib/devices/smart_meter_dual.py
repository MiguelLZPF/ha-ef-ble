import struct

from ..packet import Packet
from ..pb import bk622_common_pb2
from ..props import Field
from . import smart_meter

# Channel 2 is sent in the same DisplayPropertyUpload as channel 1, in field numbers the
# bk622_common proto does not define yet (they arrive as unknown fields):
#   985-987 voltage L1-L3, 988-990 current L1-L3, 991-993 power L1-L3,
#   994-996 phase flags L1-L3, 997 data record (GridConnectionDataRecord layout),
#   998 channel total power
_CH2_TOTAL_POWER = 998
_CH2_VOLTAGE = 984  # + clamp number 1-3
_CH2_CURRENT = 987
_CH2_POWER = 990
_CH2_FLAG = 993


def _wire_fields(buf: bytes) -> dict[int, float | int | bytes]:
    """
    Decode the top-level fields of a serialized protobuf message by field number

    Last value wins; decoding stops at an unsupported wire type or truncated data.
    """
    out: dict[int, float | int | bytes] = {}
    i = 0

    def varint() -> int:
        nonlocal i
        shift = value = 0
        while True:
            byte = buf[i]
            i += 1
            value |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                return value

    try:
        while i < len(buf):
            key = varint()
            number, wire_type = key >> 3, key & 0x07
            match wire_type:
                case 0:
                    out[number] = varint()
                case 1:
                    out[number] = struct.unpack_from("<d", buf, i)[0]
                    i += 8
                case 2:
                    length = varint()
                    out[number] = buf[i : i + length]
                    i += length
                case 5:
                    out[number] = struct.unpack_from("<f", buf, i)[0]
                    i += 4
                case _:
                    break
    except (IndexError, struct.error):
        pass
    return out


class Device(smart_meter.Device):
    """Smart Meter Dual CT"""

    SN_PREFIX = (b"ES81",)
    NAME_PREFIX = "EF-ES8"

    # CT channel 2 - the channel the EcoFlow app labels as solar
    pv_power_sum = Field[float]()

    # CT channel 2 per clamp (L1-L3), decoded from the unknown fields 985-996
    ct2_l1_power = Field[float]()
    ct2_l2_power = Field[float]()
    ct2_l3_power = Field[float]()
    ct2_l1_current = Field[float]()
    ct2_l2_current = Field[float]()
    ct2_l3_current = Field[float]()
    ct2_l1_voltage = Field[float]()
    ct2_l2_voltage = Field[float]()
    ct2_l3_voltage = Field[float]()
    ct2_l1_active = Field[bool]()
    ct2_l2_active = Field[bool]()
    ct2_l3_active = Field[bool]()

    def _update_ct2(self, payload: bytes):
        wire = _wire_fields(payload)

        total = wire.get(_CH2_TOTAL_POWER)
        if isinstance(total, float):
            self.pv_power_sum = round(total, 1)

        for n in (1, 2, 3):
            for base, name, digits in (
                (_CH2_POWER, "power", 2),
                (_CH2_CURRENT, "current", 2),
                (_CH2_VOLTAGE, "voltage", 1),
            ):
                value = wire.get(base + n)
                if isinstance(value, float):
                    setattr(self, f"ct2_l{n}_{name}", round(value, digits))

            flag = wire.get(_CH2_FLAG + n)
            if isinstance(flag, int):
                setattr(self, f"ct2_l{n}_active", bool(flag))
                if not flag:
                    # same rule as CT1: an inactive phase reads 0
                    setattr(self, f"ct2_l{n}_power", 0)
                    setattr(self, f"ct2_l{n}_current", 0)
                    setattr(self, f"ct2_l{n}_voltage", 0)

    async def data_parse(self, packet: Packet):
        processed = False
        self.reset_updated()

        match packet.src, packet.cmd_set, packet.cmd_id:
            case (0x02, 0xFE, 0x15):
                self.update_from_bytes(
                    bk622_common_pb2.DisplayPropertyUpload, packet.payload
                )
                self._update_ct2(packet.payload)
                processed = True

        if not self.l1_active:
            self.l1_power = self.l1_current = self.l1_voltage = 0
        if not self.l2_active:
            self.l2_power = self.l2_current = self.l2_voltage = 0
        if not self.l3_active:
            self.l3_power = self.l3_current = self.l3_voltage = 0

        for field_name in self.updated_fields:
            self.update_callback(field_name)
            self.update_state(field_name, getattr(self, field_name))

        return processed
