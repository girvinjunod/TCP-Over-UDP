import struct
import sys


def bytes2hexstring(byte_obj):
    return ''.join('{:02x}'.format(x) for x in byte_obj)


class SegmentFlagType():
    DATA = b"\x00"
    SYN = b"\x02"
    FIN = b"\x01"
    ACK = b"\x10"
    SYNACK = b"\x12"

    def getFlag(flag: bytes):
        if flag == SegmentFlagType.DATA:
            return "Data"
        elif flag == SegmentFlagType.SYN:
            return "Syn"
        elif flag == SegmentFlagType.FIN:
            return "Fin"
        elif flag == SegmentFlagType.ACK:
            return "Ack"
        elif flag == SegmentFlagType.SYNACK:
            return "Syn Ack"
        else:
            return "Unknown"


class Segment():
    # Bytes 0 - 3: Seq Num
    # Bytes 4 - 7: Ack Num
    # Bytes 8 - 11: Flags, Empty, Checksum (Byte 10 - 11)
    # Bytes 12 - MAX: Data (Max 32768 Bytes)

    # Convert data into byte array to avoid null byte error

    def __init__(self, seqnum, acknum, flagtype, data):
        self.seqnum_data = seqnum
        self.acknum_data = acknum
        self.flagtype_data = flagtype

        self.set_seqnum(seqnum)
        self.set_acknum(acknum)
        self.set_flagtype(flagtype)
        self.set_data(data)
        self.set_checksum()
        self.buffer = self.build()

    def set_seqnum(self, seqnum: int):
        self.seqnum = struct.pack('4s', seqnum.to_bytes(4, byteorder="big"))

    def set_acknum(self, acknum: int):
        self.acknum = struct.pack('4s', acknum.to_bytes(4, byteorder="big"))

    def set_flagtype(self, _flagtype):
        self.flagtype = struct.pack('c', _flagtype)

    def set_checksum(self):
        checksum = self.calc_checksum(
            self.seqnum, self.acknum, self.flagtype, self.data)
        self.checksum = struct.pack(
            '2s', checksum.to_bytes(2, byteorder="big"))

    def set_data(self, data):
        if sys.getsizeof(data) > 32768:
            print("Data is too big for segment")
        else:
            self.data = struct.pack('{}s'.format(sys.getsizeof(data)), data)

    # TODO: checksum error
    def calc_checksum(self, seqnum, acknum, _flagtype, data):
        sum = 0x00
        data = seqnum + acknum + _flagtype + data
        length_data = len(data)
        if (length_data % 2 != 0):
            length_data += 1
            data += struct.pack('!B', 0)
        # print(data)
        sum = (data[0] << 8) + (data[1])
        for i in range(2, length_data, 2):
            w = (data[i] << 8) + (data[i+1])
            sum = sum + w
        return (~sum & 0xFFFF)

        # words = list((data >> i) & 0xFF for i in range(0, len(data), 2))
        # for word in words:
        #     sum += word
        #     sum = (sum & 0xffff) + (sum >> 16)
        # return (~sum & 0xffff)

    # TODO: build error
    def build(self):
        # max_data = 32768
        return struct.pack('4s4scc2s{}s'.format(sys.getsizeof(self.data)), self.seqnum, self.acknum, self.flagtype, b'\x00', self.checksum, self.data)

    def __str__(self):
        return f'{bytes2hexstring(self.seqnum)} \
{bytes2hexstring(self.acknum)} \
{bytes2hexstring(self.flagtype)} \
{bytes2hexstring(self.checksum)} \
{bytes2hexstring(self.data)}'


class SegmentUnwrapper():
    def __init__(self, payload: str):

        self.raw_buffer = payload
        self.raw_seqnum = payload[0:4]
        self.raw_acknum = payload[4:8]
        self.raw_type = payload[8]
        self.raw_checksum = payload[10:12]

        self.get_segment_type()
        self.get_segment_seqnum()
        self.get_segment_acknum()
        self.get_segment_data()
        self.get_segment_checksum()
        # self.is_valid = self.verify_integrity()


    def get_segment_type(self):
        self.flagtype = self.raw_type.to_bytes(1, byteorder="big")

    def get_segment_seqnum(self):
        self.seqnum = int(struct.unpack(">I", self.raw_seqnum)[0])

    def get_segment_acknum(self):
        self.acknum = int(struct.unpack(">I", self.raw_acknum)[0])

    def get_segment_checksum(self):
        self.checksum = int(struct.unpack(">H", self.raw_checksum)[0])
        # print(self.checksum)

    def get_segment_data(self):
        self.data = self.raw_buffer[7:]

    # TODO: verify_integrity error
    def verify_integrity(self):
        data = self.raw_type + self.raw_seqnum + self.raw_acknum + self.data
        sum = 0x00
        data_len = len(data)
        if (data_len % 2 != 0):
            data_len += 1
            data += struct.pack('!B', 0)

        sum = (data[0] << 8) + (data[1])
        for i in range(2, data_len, 2):
            w = (data[i] << 8) + (data[i+1])
            sum += w
        sum = ~sum & 0xFFFF
        sum = struct.pack('2s', sum.to_bytes(2, byteorder="big"))
        return True if sum == self.raw_checksum else False

    def __str__(self):
        return f'{self.raw_type} \
{self.raw_seqnum} \
{self.raw_acknum}'

# if __name__ == '__main__':
#     # file = open("test.txt", "r")
#   ()
