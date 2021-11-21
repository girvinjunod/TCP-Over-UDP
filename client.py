import socket
import logging
import sys
from segment import *

HOST = socket.gethostbyname(socket.gethostname())
CLIENT_SEQUENCE_NUM = 1
DEFAULT_BUFFER_SIZE = 8208*4

# Client to send data to server on UDP port
# Perform three way handshake on found
# On successful handshake receive data to server

def setup_client(PORT, FILE_PATH):
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  logging.info(f'Client started at port {PORT}...')

  # Search for server in broadcast address
  logging.info(f'Client ({HOST}, {PORT}) searching server in broadcast address')
  
  # Build segment
  segment = Segment(CLIENT_SEQUENCE_NUM, 0, SegmentFlagType.SYN, ''.encode())
  s.sendto(segment.buffer, (HOST, PORT))
  
  # Perform three way handshake with server
  three_way_success = False
  while not three_way_success:
    msg, addr = s.recvfrom(DEFAULT_BUFFER_SIZE)
    logging.info(f'Server found at {addr}, performing three way handshake..')

    # Unwrap segment
    segment_received = SegmentUnwrapper(msg)
    logging.info(f'Segment SEQ={segment.seqnum_data}: Sent {SegmentFlagType.getFlag(segment.flagtype_data)}')

    # Receive SYN ACK segment from server
    if segment_received.flagtype == SegmentFlagType.SYNACK and segment_received.acknum == segment.seqnum_data + 1:
      # Send response segment
      response_segment = Segment(CLIENT_SEQUENCE_NUM+1, segment_received.seqnum+1, SegmentFlagType.ACK, ''.encode())
      s.sendto(response_segment.build(), addr)
      logging.info(f'Segment SEQ={segment_received.seqnum}: Received {SegmentFlagType.getFlag(segment_received.flagtype)}, Sent {SegmentFlagType.getFlag(response_segment.flagtype_data)}')
      three_way_success = True
    else:
      logging.error(f'Received unknown flag from {addr}')

  # Receive data from server
  logging.info(f'Waiting data from server...')
  with open(FILE_PATH, 'wb') as f:
    while True:
      msg, addr = s.recvfrom(DEFAULT_BUFFER_SIZE)
      data_received = SegmentUnwrapper(msg)
      if data_received.flagtype == SegmentFlagType.DATA:

        if data_received.data:
          response_data = Segment(CLIENT_SEQUENCE_NUM, data_received.seqnum+1, SegmentFlagType.ACK, ''.encode())
          s.sendto(response_data.build(), addr)

          logging.info(f'Segment SEQ={data_received.seqnum}: Received {SegmentFlagType.getFlag(data_received.flagtype)}, Sent {SegmentFlagType.getFlag(response_data.flagtype)}')
          f.write(data_received.data)
        else:
          logging.error(f'Received empty data from {addr}')
      elif data_received.flagtype == SegmentFlagType.FIN:
        logging.info(f'Data received successfuly! File saved at {FILE_PATH}')
        break

    f.close()

if __name__ == '__main__':
  n_args = len(sys.argv)

  formatter = logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)
  if n_args != 3:
    logging.error("{} arguments given, expected 2".format(n_args-1))
    sys.exit()

  PORT = int(sys.argv[1])
  FILE_PATH = sys.argv[2]
  setup_client(PORT, FILE_PATH)
