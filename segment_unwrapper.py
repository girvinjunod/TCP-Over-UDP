import struct

class SegmentUnwrapper():
    def __init__(self, payload: str):

        self.raw_buffer = payload
        self.raw_seqnum = payload[0:4]
        self.raw_acknum = payload[4:8]
        self.raw_type = payload[8]
        self.raw_checksum = payload[10:12]
        self.raw_data = payload[12:]

        self.get_segment_type()
        self.get_segment_seqnum()
        self.get_segment_acknum()
        self.get_segment_data()
        self.get_segment_checksum()
        self.is_valid = self.verify_integrity()

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
        self.data = self.raw_data.rstrip(b'\x00')

    # TODO: verify_integrity error
    def verify_integrity(self):
        data = self.flagtype + self.raw_seqnum + self.raw_acknum + self.raw_data
        sum = 0x00
        data_len = len(data)
        if (data_len % 2 != 0):
            data_len += 1
            data += struct.pack('!B', 0)

        # sum = (data[0] << 8) + (data[1])
        for i in range(0, data_len, 2):
            w = (data[i] << 8) + (data[i+1])
            sum += w
        sum = (sum >> 16) + (sum & 0xFFFF)
        sum = ~sum & 0xFFFF
        sum = struct.pack('2s', sum.to_bytes(2, byteorder="big"))
        self.sum = sum
        return True if sum == self.raw_checksum else False

    def __str__(self):
        return f'{self.raw_type} \
{self.seqnum} \
{self.acknum} \
{self.checksum}'
