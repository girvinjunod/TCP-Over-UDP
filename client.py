import os
import socket
import logging
import sys
from typing import Tuple
from segment import *

HOST = socket.gethostbyname(socket.gethostname())
CLIENT_SEQUENCE_NUM = 1
BUFFER_SIZE = 8208*4

def listening_segment(sock: socket, segment_type: SegmentFlagType) -> Tuple[bool, Segment, tuple]:
  msg, addr = sock.recvfrom(BUFFER_SIZE)

  # Unwrap client message
  segment_received = SegmentUnwrapper(msg)

  # Check segment flag type
  if segment_received.flagtype == segment_type:
    return True, segment_received, addr

  return False, segment_received, addr

def three_way_handshake_client(sock, syn_segment):
  # Performing three way handshake with server
  three_way_success = False
  sock.sendto(syn_segment.buffer, (HOST, PORT))

  # Listening for SYNACK segment from servr
  valid, synack_segment, addr = listening_segment(sock, SegmentFlagType.SYNACK)
  logging.info(f'Server found at {addr}, performing three way handshake..')
  logging.info(f'Segment SEQ={syn_segment.seqnum_data}: Sent {SegmentFlagType.getFlag(syn_segment.flagtype_data)}')

  # Receive SYN ACK segment from server
  if valid:
    # Send response segment
    ack_segment = Segment(CLIENT_SEQUENCE_NUM+1, synack_segment.seqnum+1, SegmentFlagType.ACK, ''.encode())
    sock.sendto(ack_segment.build(), addr)
    logging.info(f'Segment SEQ={synack_segment.seqnum}: Received {SegmentFlagType.getFlag(synack_segment.flagtype)}, Sent {SegmentFlagType.getFlag(ack_segment.flagtype_data)}')
    three_way_success = True
  else:
    logging.info(f'Received unknown flag! Retrying three way handshake..')

  return three_way_success

def receive_data(sock: socket, file):
  success = True
  while success:
    valid, data_segment, addr = listening_segment(sock, SegmentFlagType.DATA)
    if valid:

      if data_segment.data:
        ack_segment = Segment(CLIENT_SEQUENCE_NUM, data_segment.seqnum+1, SegmentFlagType.ACK, ''.encode())
        sock.sendto(ack_segment.build(), addr)

        logging.info(f'Segment SEQ={data_segment.seqnum}: Received {SegmentFlagType.getFlag(data_segment.flagtype)}, Sent {SegmentFlagType.getFlag(ack_segment.flagtype)}')
        file.write(data_segment.data)

      else:
        logging.info(f'Received empty data from {addr}')

    elif data_segment.flagtype == SegmentFlagType.FIN:
      logging.info(f'Data received successfuly! File saved at {FILE_PATH}')
      break
    
    else:
      logging.info(f'Segment flagtype not recognized!')
      success = False
  
  return success

def setup_client(PORT, FILE_PATH):
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  logging.info(f'Client started at port {PORT}...')

  # Search for server in broadcast address
  logging.info(f'Client ({HOST}, {PORT}) connecting to server in broadcast address')
  
  # Build segment
  segment = Segment(CLIENT_SEQUENCE_NUM, 0, SegmentFlagType.SYN, ''.encode())
  
  # Perform three way handshake with server
  three_way_success = False
  while not three_way_success:
    try:
      three_way_success = three_way_handshake_client(s, segment)
    except:
      logging.error(f'Error occured during three way handshake with server!')

  # Receive data from server
  logging.info(f'Waiting data from server...')
  with open(FILE_PATH, 'wb') as f:
    try:
      success = receive_data(s, f)
      if not success:
        os.remove(FILE_PATH)
    except:
      logging.error(f'Error occured during receiving data from server!')
      os.remove(FILE_PATH)

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
