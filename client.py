import os
import socket
import logging
import sys
from typing import Tuple
from segment import *

HOST = socket.gethostbyname(socket.gethostname())
CLIENT_SEQUENCE_NUM = 0
BUFFER_SIZE = 32780

def listening_segment(sock: socket, segment_type: SegmentFlagType) -> Tuple[bool, SegmentUnwrapper, tuple]:
  msg, addr = sock.recvfrom(BUFFER_SIZE)

  # Unwrap client message
  segment_received = SegmentUnwrapper(msg)

  # Check segment flag type
  if segment_received.flagtype == segment_type:
    return segment_received.is_valid, segment_received, addr

  return False, segment_received, addr

def three_way_handshake_client(sock):
  # Listening for SYN segment
  valid, syn_segment, addr = listening_segment(sock, SegmentFlagType.SYN)

  if valid:

    # Send SYN-ACK segment to server
    synack_segment = Segment(
      CLIENT_SEQUENCE_NUM, syn_segment.seqnum+1, SegmentFlagType.SYNACK, b'')
    sock.sendto(synack_segment.build(), addr)
    logging.info(f'Segment SEQ={syn_segment.seqnum}: Received {SegmentFlagType.getFlag(syn_segment.flagtype)}, Sent {SegmentFlagType.getFlag(synack_segment.flagtype)}')

    # Receive ACK segment from server
    valid, ack_segment, addr = listening_segment(sock, SegmentFlagType.ACK)

    if valid:
      logging.info(f'Segment SEQ={ack_segment.seqnum}: Received {SegmentFlagType.getFlag(ack_segment.flagtype)}')
      return True

  return False

def receive_data(sock: socket, file):
  # 	Rn := 0
	#   Do the following forever:
  #   	if the packet received = Rn and the packet is error free then
  #       	Accept the packet and send it to a higher layer
  #       	Rn := Rn + 1
  #   	else
  #       	Refuse packet
  #   	Send acknowledgement for last received packet
  base = 0
  data_ret = b''
  while True:
    valid, data_segment, addr = listening_segment(sock, SegmentFlagType.DATA)
    if valid and data_segment.seqnum == base: # and check_sum success

      if data_segment.data:
        ack_segment = Segment(CLIENT_SEQUENCE_NUM, data_segment.seqnum+1, SegmentFlagType.ACK, ''.encode())
        sock.sendto(ack_segment.buffer, addr)

        logging.info(f'Segment SEQ={data_segment.seqnum}: Received {SegmentFlagType.getFlag(data_segment.flagtype)}, Sent {SegmentFlagType.getFlag(ack_segment.flagtype)}')
        # file.write(data_segment.data)
        data_ret += data_segment.data

      else:
        logging.info(f'Received empty data from {addr}')
      
      base += 1

    elif data_segment.flagtype == SegmentFlagType.FIN:
      logging.info(f'Data received successfuly! File saved at {FILE_PATH}')
      break

    elif not valid or data_segment.seqnum > base: # Damaged segment
      refuse_segment = Segment(CLIENT_SEQUENCE_NUM, base, SegmentFlagType.SYN, b'')
      sock.sendto(refuse_segment.buffer, addr)

      logging.warning(f'Segment SEQ={data_segment.seqnum}: Segment refused, Ack SEQ={base}.')
  
  return data_ret

def setup_client(PORT, FILE_PATH):
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  logging.info(f'Client started at port {PORT}...')

  # Search for server in broadcast address
  s.sendto(b'', (HOST, PORT))
  logging.info(f'Client ({HOST}, {PORT}) connecting to server in broadcast address')
  
  # Waiting for server to initiate three way handshake
  three_way_success = False
  try:
    three_way_success = three_way_handshake_client(s)
  except:
    logging.error(f'Error occured during three way handshake with server!')

  # Terminate client if three way handshake failed
  if not three_way_success:
    logging.error(f'Three way handshake failed! Terminating client...')
    return

  # Receive data from server
  logging.info(f'Three way handshake successful! Waiting data from server...')
  with open(FILE_PATH, 'wb') as f:
    try:
      data = receive_data(s, f)
      if not data:
        os.remove(FILE_PATH)
      else:
        f.write(data)
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
