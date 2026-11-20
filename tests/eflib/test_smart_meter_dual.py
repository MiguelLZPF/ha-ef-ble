import struct

import pytest
from pytest_mock import MockerFixture

from custom_components.ef_ble.eflib.devices.smart_meter_dual import Device
from custom_components.ef_ble.eflib.packet import Packet
from custom_components.ef_ble.eflib.pb import bk622_common_pb2

# CT2 field numbers, see the comment at the top of smart_meter_dual.py
VOLTAGE, CURRENT, POWER, FLAG, TOTAL = 985, 988, 991, 994, 998


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _float_field(number: int, value: float) -> bytes:
    return _varint(number << 3 | 5) + struct.pack("<f", value)


def _flag_field(number: int, value: bool) -> bytes:
    return _varint(number << 3) + _varint(int(value))


def _ct1(active=(True, True, True)) -> bytes:
    msg = bk622_common_pb2.DisplayPropertyUpload()
    msg.grid_connection_vol_L1 = 231.5
    msg.grid_connection_amp_L1 = 1.25
    msg.grid_connection_power_L1 = 289.0
    msg.grid_connection_flag_L1 = active[0]
    msg.grid_connection_flag_L2 = active[1]
    msg.grid_connection_flag_L3 = active[2]
    return msg.SerializeToString()


def _ct2(
    volts=(230.0, 229.0, 228.0),
    amps=(1.0, 2.0, 3.0),
    watts=(100.0, 200.0, 300.0),
    flags=(True, True, True),
    total=600.0,
) -> bytes:
    out = b""
    for i in range(3):
        out += _float_field(VOLTAGE + i, volts[i])
        out += _float_field(CURRENT + i, amps[i])
        out += _float_field(POWER + i, watts[i])
        out += _flag_field(FLAG + i, flags[i])
    return out + _float_field(TOTAL, total)


def _packet(payload: bytes) -> Packet:
    return Packet(0x02, 0x20, 0xFE, 0x15, payload)


@pytest.fixture
def device(mocker: MockerFixture):
    ble_dev = mocker.Mock()
    ble_dev.address = "AA:BB:CC:DD:EE:FF"
    adv_data = mocker.MagicMock()
    device = Device(ble_dev, adv_data, "ES81Z00000000000")
    device._conn = mocker.AsyncMock()
    return device


async def test_ct2_fields_land_on_the_right_clamp(device):
    assert await device.data_parse(_packet(_ct1() + _ct2())) is True

    assert device.ct2_l1_voltage == 230.0
    assert device.ct2_l2_voltage == 229.0
    assert device.ct2_l3_voltage == 228.0
    assert device.ct2_l1_current == 1.0
    assert device.ct2_l2_current == 2.0
    assert device.ct2_l3_current == 3.0
    assert device.ct2_l1_power == 100.0
    assert device.ct2_l2_power == 200.0
    assert device.ct2_l3_power == 300.0
    assert device.ct2_l1_active is True


async def test_ct1_decode_is_unchanged(device):
    await device.data_parse(_packet(_ct1() + _ct2()))

    assert device.l1_voltage == 231.5
    assert device.l1_current == 1.25
    assert device.l1_power == 289.0


async def test_channel_total_is_kept(device):
    await device.data_parse(_packet(_ct1() + _ct2(total=612.34)))

    assert device.pv_power_sum == 612.3


async def test_inactive_flag_zeroes_only_its_clamp(device):
    await device.data_parse(_packet(_ct1() + _ct2(flags=(True, False, True))))

    assert device.ct2_l2_active is False
    assert device.ct2_l2_power == 0
    assert device.ct2_l2_current == 0
    assert device.ct2_l2_voltage == 0
    assert device.ct2_l1_power == 100.0
    assert device.ct2_l3_power == 300.0


async def test_payload_without_ct2_leaves_fields_untouched(device):
    await device.data_parse(_packet(_ct1() + _ct2()))
    await device.data_parse(_packet(_ct1()))

    assert device.ct2_l1_power == 100.0
    assert device.ct2_l3_voltage == 228.0
    assert device.pv_power_sum == 600.0


async def test_payload_without_ct2_on_new_device_sets_nothing(device):
    await device.data_parse(_packet(_ct1()))

    assert device.ct2_l1_power is None
    assert device.ct2_l1_active is None
    assert device.pv_power_sum is None


@pytest.mark.parametrize("cut", [1, 2, 3, 5, 9])
async def test_truncated_payload_does_not_raise(device, cut):
    payload = _ct1() + _ct2()
    await device.data_parse(_packet(payload[:-cut]))
