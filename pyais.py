"""
Decoding AIS messages in Python

Performance considerations:

Even though performance is not my primary concern, the code shouldn't be too slow.
I tried a few different straight forward approaches for decoding the messages and compared their performance:

Using native python strings and converting each substring into an integer:
    -> Decoding #8000 messages takes 1.132967184 seconds

Using bitstring's BitArray and slicing:
    -> Decoding #8000 AIS messages takes 2.699436055 seconds

Using the bitarray module:
    -> because their is not native to_int method, the code gets utterly cluttered

"""

import socket
from math import ceil
from bitstring import BitArray

UNDEFINED = 'Undefined'
RESERVED = 'Reserved'

# Constants
NAVIGATION_STATUS = {
    0: 'Under way using engine',
    1: 'At anchor',
    2: 'Not under command',
    3: 'Restricted manoeuverability',
    4: 'Constrained by her draught',
    5: 'Moored',
    6: 'Aground',
    7: 'Engaged in Fishing',
    8: 'Under way sailing',
    9: 'Reserved',
    10: 'Reserved',
    11: 'Reserved',
    12: 'Reserved',
    13: 'Reserved',
    14: 'AIS-SART is active',
    15: 'Undefined',
}

MANEUVER_INDICATOR = {
    0: 'Not available',
    1: 'No special maneuver',
    2: 'Special maneuver'
}

EPFD_TYPE = {
    0: 'Undefined',
    1: 'GPS',
    2: 'GLONASS',
    3: 'GPS/GLONASS',
    4: 'Loran-C',
    5: 'Chayka',
    6: 'Integrated navigation system',
    7: 'Surveyed',
    8: 'Galileo',
}

SHIP_TYPE = {
    0: 'Not available',
    20: 'Wing in ground (WIG)',
    21: 'Wing in ground (WIG), Hazardous category A',
    22: 'Wing in ground (WIG), Hazardous category B',
    23: 'Wing in ground (WIG), Hazardous category C',
    24: 'Wing in ground (WIG), Hazardous category D',
    25: 'WIG Reserved',
    26: 'WIG Reserved',
    27: 'WIG Reserved',
    28: 'WIG Reserved',
    29: 'WIG Reserved',
    30: 'Fishing',
    31: 'Towing',
    32: 'Towing,length exceeds 200m or breadth exceeds 25m',
    33: 'Dredging or underwater ops',
    34: 'Diving ops',
    35: 'Military ops',
    36: 'Sailing',
    37: 'Pleasure Craft',
    38: 'Reserved',
    39: 'Reserved',
    40: 'High speed craft (HSC)',
    41: 'High speed craft (HSC), Hazardous category A',
    42: 'High speed craft (HSC), Hazardous category B',
    43: 'High speed craft (HSC), Hazardous category C',
    44: 'High speed craft (HSC), Hazardous category D',
    45: 'High speed craft (HSC), Reserved',
    46: 'High speed craft (HSC), Reserved',
    47: 'High speed craft (HSC), Reserved',
    48: 'High speed craft (HSC), Reserved',
    49: 'High speed craft (HSC), No additional information',
    50: 'Pilot Vessel',
    51: 'Search and Rescue vessel',
    52: 'Tug',
    53: 'Port Tender',
    54: 'Anti-pollution equipment',
    55: 'Law Enforcement',
    56: 'Spare - Local Vessel',
    57: 'Spare - Local Vessel',
    58: 'Medical Transport',
    59: 'Noncombatant ship according to RR Resolution No. 18',
    60: 'Passenger',
    61: 'Passenger, Hazardous category A',
    62: 'Passenger, Hazardous category B',
    63: 'Passenger, Hazardous category C',
    64: 'Passenger, Hazardous category D',
    65: 'Passenger, Reserved',
    66: 'Passenger, Reserved',
    67: 'Passenger, Reserved',
    68: 'Passenger, Reserved',
    69: 'Passenger, No additional information',
    70: 'Cargo',
    71: 'Cargo, Hazardous category A',
    72: 'Cargo, Hazardous category B',
    73: 'Cargo, Hazardous category C',
    74: 'Cargo, Hazardous category D',
    75: 'Cargo, Reserved',
    76: 'Cargo, Reserved',
    77: 'Cargo, Reserved',
    78: 'Cargo, Reserved',
    79: 'Cargo, No additional information',
    80: 'Tanker',
    81: 'Tanker, Hazardous category A',
    82: 'Tanker, Hazardous category B',
    83: 'Tanker, Hazardous category C',
    84: 'Tanker, Hazardous category D',
    85: 'Tanker, Reserved ',
    86: 'Tanker, Reserved ',
    87: 'Tanker, Reserved ',
    88: 'Tanker, Reserved ',
    89: 'Tanker, No additional information',
    90: 'Other Type',
    91: 'Other Type, Hazardous category A',
    92: 'Other Type, Hazardous category B',
    93: 'Other Type, Hazardous category C',
    94: 'Other Type, Hazardous category D',
    95: 'Other Type, Reserved',
    96: 'Other Type, Reserved',
    97: 'Other Type, Reserved',
    98: 'Other Type, Reserved',
    99: 'Other Type, No additional information'
}

DAC_FID = {
    '1-12': 'Dangerous cargo indication',
    '1-14': 'Tidal window',
    '1-16': 'Number of persons on board',
    '1-18': 'Clearance time to enter port',
    '1-20': 'Berthing data (addressed)',
    '1-23': 'Area notice (addressed)',
    '1-25': 'Dangerous Cargo indication',
    '1-28': 'Route info addressed',
    '1-30': 'Text description addressed',
    '1-32': 'Tidal Window',
    '200-21': 'ETA at lock/bridge/terminal',
    '200-22': 'RTA at lock/bridge/terminal',
    '200-55': 'Number of persons on board',
    '235-10': 'AtoN monitoring data (UK)',
    '250-10': 'AtoN monitoring data (ROI)',

}


def decode_ascii6(data):
    """
    Decode AIS_ASCII_6 encoded data and convert it into binary.
    :param data: ASI_ASCII_6 encoded data
    :return: a binary string of 0's and 1's, e.g. 011100 011111 100001
    """
    binary_string = ''

    for c in data:
        c = ord(c) - 48
        if c > 40:
            c -= 8
        binary_string += f'{c:06b}'

    return binary_string


def split_str(string, chunk_size=6):
    """
    Split a string into equal sized chunks and return these as a list.
    The last substring may not have chunk_size chars,
    if len(string) is not a multiple of chunk_size.

    :param string: arbitrary string
    :param chunk_size: chunk_size
    :return: a list of substrings of chunk_size
    """
    chunks = ceil(len(string) / chunk_size)
    lst = [string[i * chunk_size:(i + 1) * chunk_size] for i in range(chunks)]
    return lst


def ascii6(data, ignore_tailing_fillers=True):
    """
    Decode bit sequence into ASCII6.
    :param data: ASI_ASCII_6 encoded data
    :return: ASCII String
    """
    string = ""
    for c in split_str(data):
        c = int(c, 2)
        if c < 32:
            c += 64
        c = chr(c)

        if ignore_tailing_fillers and c == '@':
            return string
        string += c

    return string


def signed(bit_vector):
    """
    convert bit sequence to signed integer
    :param bit_vector: bit sequence
    :return: singed int
    """
    b = BitArray(bin=bit_vector)
    return b.int


def to_int(bit_string, base=2):
    """
    Convert a sequence of bits to int while ignoring empty strings
    :param bit_string: sequence of zeros and ones
    :param base: the base
    :return: a integer or None if no valid bit_string was provided
    """
    if bit_string:
        return int(bit_string, base)
    return 0


def checksum(msg):
    """
    Compute the checksum of a given message
    :param msg: message
    :return: hex
    """

    c_sum = 0
    for c in msg[1::]:
        if c == '*':
            break
        c_sum ^= ord(c)

    return c_sum


def decode_msg_1(bit_vector):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    status = to_int(bit_vector[38:42], 2)
    maneuver = to_int(bit_vector[143:145], 2)
    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'status': (status, NAVIGATION_STATUS[status]),
        'turn': signed(bit_vector[42:50]),
        'speed': to_int(bit_vector[50:60], 2),
        'accuracy': to_int(bit_vector[60], 2),
        'lon': signed(bit_vector[61:89]) / 600000.0,
        'lat': signed(bit_vector[89:116]) / 600000.0,
        'course': to_int(bit_vector[116:128], 2) * 0.1,
        'heading': to_int(bit_vector[128:137], 2),
        'second': to_int(bit_vector[137:143], 2),
        'maneuver': (maneuver, MANEUVER_INDICATOR[maneuver]),
        'raim': bool(to_int(bit_vector[148], 2)),
        'radio': to_int(bit_vector[149::], 2)
    }


def decode_msg_2(bit_vector):
    """AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    return decode_msg_1(bit_vector)


def decode_msg_3(bit_vector):
    """
    AIS Vessel position report using ITDMA (Incremental Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    return decode_msg_1(bit_vector)


def decode_msg_4(bit_vector):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_4_base_station_report
    """
    epfd = to_int(bit_vector[134:138], 2)
    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'year': to_int(bit_vector[38:52], 2),
        'month': to_int(bit_vector[52:56]),
        'day': to_int(bit_vector[56:61], 2),
        'hour': to_int(bit_vector[61:66], 2),
        'minute': to_int(bit_vector[66:72], 2),
        'second': to_int(bit_vector[72:78], 2),
        'accuracy': bool(to_int(bit_vector[78], 2)),
        'lon': signed(bit_vector[66:72]) / 600000.0,
        'lat': signed(bit_vector[66:72]) / 600000.0,
        'epfd': (epfd, EPFD_TYPE[epfd] if epfd in EPFD_TYPE.keys() else UNDEFINED),
        'raim': bool(to_int(bit_vector[148], 2)),
        'radio': to_int(bit_vector[148::], 2)
    }


def decode_msg_5(bit_vector):
    epfd = to_int(bit_vector[270:274], 2)
    ship_type = to_int(bit_vector[66:72], 2)

    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'ais_version': to_int(bit_vector[38:40], 2),
        'imo': to_int(bit_vector[40:70], 2),
        'callsign': ascii6(bit_vector[70:112]),
        'shipname': ascii6(bit_vector[112:232]),
        'shiptype': (ship_type, SHIP_TYPE[ship_type] if ship_type in SHIP_TYPE.keys() else UNDEFINED),
        'to_bow': to_int(bit_vector[240:249], 2),
        'to_stern': to_int(bit_vector[249:258], 2),
        'to_port': to_int(bit_vector[258:264], 2),
        'to_starboard': to_int(bit_vector[264:270], 2),
        'epfd': (epfd, EPFD_TYPE[epfd]),
        'month': to_int(bit_vector[274:278], 2),
        'day': to_int(bit_vector[278:283], 2),
        'hour': to_int(bit_vector[283:288], 2),
        'minute': to_int(bit_vector[288:294], 2),
        'draught': to_int(bit_vector[294:302], 2) / 10.0,
        'destination': ascii6(bit_vector[302::])
    }


def decode_msg_6(bit_vector):
    pass


def decode_msg_7(bit_vector):
    pass


def decode_msg_8(bit_vector):
    pass


def decode_msg_9(bit_vector):
    pass


def decode_msg_10(bit_vector):
    pass


def decode_msg_11(bit_vector):
    pass


def decode_msg_12(bit_vector):
    pass


def decode_msg_13(bit_vector):
    pass


def decode_msg_14(bit_vector):
    pass


def decode_msg_15(bit_vector):
    pass


def decode_msg_16(bit_vector):
    pass


def decode_msg_17(bit_vector):
    pass


def decode_msg_18(bit_vector):
    """
    Standard Class B CS Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_18_standard_class_b_cs_position_report
    """
    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'speed': to_int(bit_vector[46:55], 2),
        'accuracy': bool(to_int(bit_vector[55], 2)),
        'lon': signed(bit_vector[56:85]) / 600000.0,
        'lat': signed(bit_vector[85:112]) / 600000.0,
        'course': to_int(bit_vector[112:124], 2) * 0.1,
        'heading': to_int(bit_vector[124:133], 2),
        'second': to_int(bit_vector[133:139], 2),
        'regional': to_int(bit_vector[139:141], 2),
        'cs': bool(to_int(bit_vector[141])),
        'display': bool(to_int(bit_vector[142])),
        'dsc': bool(to_int(bit_vector[143])),
        'band': bool(to_int(bit_vector[144])),
        'msg22': bool(to_int(bit_vector[145])),
        'assigned': bool(to_int(bit_vector[146])),
        'raim': bool(to_int(bit_vector[147])),
        'radio': to_int(bit_vector[148::]),
    }


def decode_msg_19(bit_vector):
    pass


def decode_msg_20(bit_vector):
    pass


def decode_msg_21(bit_vector):
    pass


def decode_msg_22(bit_vector):
    pass


def decode_msg_23(bit_vector):
    pass


def decode_msg_24(bit_vector):
    pass


DECODE_MSG = [
    None,
    decode_msg_1,
    decode_msg_2,
    decode_msg_3,
    decode_msg_4,
    decode_msg_5,
    decode_msg_6,
    decode_msg_7,
    decode_msg_8,
    decode_msg_9,
    decode_msg_10,
    decode_msg_11,
    decode_msg_12,
    decode_msg_13,
    decode_msg_14,
    decode_msg_15,
    decode_msg_16,
    decode_msg_17,
    decode_msg_18,
    decode_msg_19,
    decode_msg_20,
    decode_msg_21,
    decode_msg_22,
    decode_msg_23,
    decode_msg_24
]


def decode(msg):
    m_typ, n_sentences, sentence_num, seq_id, channel, data, chcksum = msg.split(',')
    decoded_data = decode_ascii6(data)
    msg_type = int(decoded_data[0:6], 2)

    if checksum(msg) != int("0x" + chcksum[2::], 16):
        print(f"\x1b[31mInvalid Checksum dropping packet!\x1b[0m")
        return None

    if n_sentences != '1' or sentence_num != '1':
        print(f"\x1b[31mSentencing is not supported yet!\x1b[0m")
        return None

    if 0 < msg_type < 25:
        return DECODE_MSG[msg_type](decoded_data)

    return None


#  ################################# TEST DRIVER #################################


def ais_stream(url="ais.exploratorium.edu", port=80):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((url, port))
    while True:
        for msg in s.recv(4096).decode("utf-8").splitlines():
            yield msg


def main():
    MESSAGES = [
        "!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C",
        "!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05",
        "!AIVDM,1,1,,A,15NJQiPOl=G?m:bE`Gpt<aun00S8,0*56",
        "!AIVDM,1,1,,B,15NPOOPP00o?bIjE`UEv4?wF2HIU,0*31",
        "!AIVDM,1,1,,A,35NVm2gP00o@5k:EbbPJnwwN25e3,0*35",
        "!AIVDM,1,1,,A,B52KlJP00=l4be5ItJ6r3wVUWP06,0*7C"
    ]

    import timeit, random

    def test():
        decode(MESSAGES[random.randint(0, 5)])

    iterations = 8000
    elapsed_time = timeit.timeit(test, number=iterations)
    print(f"Decoding #{iterations} takes {elapsed_time} seconds")

    for msg in ais_stream():
        if msg and msg[0] == "!":
            print(msg)
            print(decode(msg))
        else:
            print("Unparsed msg: " + msg)


if __name__ == "__main__":
    main()
