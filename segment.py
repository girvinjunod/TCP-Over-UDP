import struct
import sys

def bytes2hexstring(byte_obj):
    return ''.join('{:02x}'.format(x) for x in byte_obj)

class SegmentFlagType():
    DATA = b"\x00"
    SYN = b"\x02"
    FIN = b"\x01"
    ACK = b"\x05"

class Segment():
    # Bytes 0 - 3: Seq Num
    # Bytes 4 - 7: Ack Num
    # Bytes 8 - 11: Flags, Empty, Checksum (Byte 10 - 11)
    # Bytes 12 - MAX: Data (Max 32768 Bytes)

    # Convert data into byte array to avoid null byte error

    def __init__(self, seqnum, acknum, flagtype, data):
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
        checksum = self.calc_checksum(self.seqnum, self.acknum, self.flagtype, self.data)
        self.checksum = struct.pack('2s', checksum.to_bytes(2, byteorder="big")) 

    def set_data(self, data):
        if sys.getsizeof(data) > 32768:
            print("Data is too big for segment")
        else:
            self.data = struct.pack('{}s'.format(len(data)), data)

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
            sum += w
        return ~sum & 0xFFFF

        # words = list((data >> i) & 0xFF for i in range(0, len(data), 2))
        # for word in words:
        #     sum += word
        #     sum = (sum & 0xffff) + (sum >> 16)
        # return (~sum & 0xffff)

    def build(self):
        return struct.pack('4s4sc2s{}s'.format(len(self.data)), self.seqnum, self.acknum, self.flagtype, self.checksum, self.data)

    def print(self):
        print(bytes2hexstring(self.seqnum))
        print(bytes2hexstring(self.acknum))
        print(bytes2hexstring(self.flagtype))
        print(bytes2hexstring(self.checksum))
        print(bytes2hexstring(self.data))
    
if __name__ == '__main__':
    # file = open("test.txt", "r")
    test = b"\xFF\xFF"
    a = Segment(15, 20, SegmentFlagType.DATA, test)
    a.print()