import sys
import socket
import logging
from segment import *

HOST = socket.gethostbyname(socket.gethostname())
BUFFER_SIZE = 1024
SERVER_SEQUENCE_NUM = 1


def setup_server(PORT, FILE_PATH):
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  s.bind((HOST, PORT))
  logging.info("SERVER listening on {}:{}".format(HOST, PORT))

  client_list = []
  # Find clients
  while True:
    msg, addr = s.recvfrom(BUFFER_SIZE)

    # Unwrap client message
    segment_received = SegmentUnwrapper(msg)

    # Three way handshake to client
    if segment_received.flagtype == SegmentFlagType.SYN:
      # Send SYN-ACK segment
      response_segment = Segment(
        SERVER_SEQUENCE_NUM, segment_received.seqnum+1, SegmentFlagType.SYNACK, b'')
      s.sendto(response_segment.build(), addr)

      # Receive ACK segment from client
      msg, addr = s.recvfrom(BUFFER_SIZE)
      segment_received = SegmentUnwrapper(msg)
      if segment_received.flagtype == SegmentFlagType.ACK and segment_received.acknum == response_segment.seqnum+1:
        logging.info(f'Client {addr} found')
        client_list.append(addr)
        cont = input('Listen more? (y/n)')
        if cont == 'y':
          pass
        else:
          break
      else:
        logging.error(f'Client {addr} failed to connect')
    else:
      logging.error(f'Client {addr} failed to connect')

  logging.info(f'{len(client_list)} clients found:')
  for i in range(len(client_list)):
    logging.info(f'{i+1}. {client_list[i]}')

  # Send message to all clients


if __name__ == '__main__':
  n_args = len(sys.argv)

  formatter = logging.basicConfig(
      format='[%(levelname)s] %(message)s', level=logging.DEBUG)
  if n_args != 3:
      logging.error("{} arguments given, expected 2".format(n_args-1))
      sys.exit()

  PORT = int(sys.argv[1])
  FILE_PATH = sys.argv[2]
  setup_server(PORT, FILE_PATH)
