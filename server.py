import sys
import socket
import logging
from typing import Tuple
from segment import *

HOST = socket.gethostbyname(socket.gethostname())
SERVER_SEQUENCE_NUM = 1
BUFFER_SIZE = 8208*4
DATA_SIZE = 32768

def listening_segment(sock: socket, segment_type: SegmentFlagType) -> Tuple[bool, Segment, tuple]:
  msg, addr = sock.recvfrom(BUFFER_SIZE)

  # Unwrap client message
  segment_received = SegmentUnwrapper(msg)

  # Check segment flag type
  if segment_received.flagtype == segment_type:
    return True, segment_received, addr

  return False, segment_received, addr

def three_way_handshake_server(sock: socket) -> Tuple[bool, tuple]:
  # Three way handshake to client
  # Listening for SYN segment
  valid, syn_segment, addr = listening_segment(sock, SegmentFlagType.SYN)

  if valid:
    # Send SYN-ACK segment to client
    synack_segment = Segment(
      SERVER_SEQUENCE_NUM, syn_segment.seqnum+1, SegmentFlagType.SYNACK, b'')
    sock.sendto(synack_segment.build(), addr)

    # Receive ACK segment from client
    valid, ack_segment, addr = listening_segment(sock, SegmentFlagType.ACK)

    if valid:
      return True, addr

  return False, addr

def send_data(sock: socket, f, client: tuple):
  # Send file
  data_sent = 0
  while True:
    # Read data
    data = f.read(DATA_SIZE)
    if not data:
      break

    # Send file name
    # filename_segment = Segment(SERVER_SEQUENCE_NUM, 0, SegmentFlagType.DATA, filename.encode())
    # s.sendto(filename_segment.build(), client)
    # SERVER_SEQUENCE_NUM += 1

    # Send file data to client
    segment_to_send = Segment(SERVER_SEQUENCE_NUM+data_sent, 0, SegmentFlagType.DATA, data)
    sock.sendto(segment_to_send.build(), client)
    logging.info(f'Segment SEQ={segment_to_send.seqnum_data}: Sent')
    data_sent += 1

  # Listening Ack from client
  data_received = 0
  while data_received < data_sent:
    valid, response_received, _ = listening_segment(sock, SegmentFlagType.ACK)
    if valid:
      logging.info(f'Segment SEQ={response_received.acknum-1}: Packet Acked')
    else:
      logging.error(f'Segment SEQ={response_received.acknum-1}: Packet not acked')
    data_received += 1

  fin_segment = Segment(SERVER_SEQUENCE_NUM, 0, SegmentFlagType.FIN, b'')
  sock.sendto(fin_segment.build(), client)
  logging.info(f'File successfuly sent to {client[0]}:{client[1]}')

def setup_server(PORT, FILE_PATH):
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  s.bind((HOST, PORT))
  logging.info("SERVER listening on {}:{}".format(HOST, PORT))

  client_list = []
  # Find clients
  while True:
    # Three way handshake with client
    try:
      three_way_success, addr = three_way_handshake_server(s)
      
      if three_way_success:
        # Add client address to list
        logging.info(f'Client {addr} found')
        client_list.append(addr)
        cont = input('Listen more? (y/n)')
      
        if cont == 'y':
          pass
        else:
          break
      
      else:
        logging.info(f'Client {addr} failed to connect! Listening for more client..')
    except:
      logging.error('Error occured during three way handshake!')

  logging.info(f'{len(client_list)} clients found:')
  for i in range(len(client_list)):
    logging.info(f'{i+1}. {client_list[i][0]}:{client_list[i][1]}')

  # Send message to all clients
  with open(FILE_PATH, 'rb') as f:

    for client in client_list:
      f.seek(0)
      try:
        send_data(s, f, client)
      except:
        logging.error(f'Error occured during sending data to {client}')
        continue

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
