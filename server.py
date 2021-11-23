import sys
import socket
import logging
from typing import List, Tuple
from segment import *

HOST = socket.gethostbyname(socket.gethostname())
SERVER_SEQUENCE_NUM = 0
BUFFER_SIZE = 32777
DATA_SIZE = 32768
WINDOW_SIZE = 5

def listening_segment(sock: socket, segment_type: SegmentFlagType) -> Tuple[bool, SegmentUnwrapper, tuple]:
  msg, addr = sock.recvfrom(BUFFER_SIZE)

  # Unwrap client message
  segment_received = SegmentUnwrapper(msg)

  # Check segment flag type
  if segment_received.flagtype == segment_type:
    return True, segment_received, addr

  return False, segment_received, addr

def three_way_handshake_server(sock: socket, client: tuple) -> bool:
  # Performing three way handshake with client
  logging.info(f'Performing three way handshake with client({client[0]}:{client[1]})..')

  # Build segment
  syn_segment = Segment(SERVER_SEQUENCE_NUM, 0, SegmentFlagType.SYN, ''.encode())
  three_way_success = False
  sock.sendto(syn_segment.buffer, client)
  logging.info(f'Segment SEQ={syn_segment.seqnum_data}: Sent {SegmentFlagType.getFlag(syn_segment.flagtype_data)}')

  # Listening for SYNACK segment from client
  valid, synack_segment, addr = listening_segment(sock, SegmentFlagType.SYNACK)

  # Receive SYN ACK segment from client
  if valid:
    # Send ack segment to client
    ack_segment = Segment(SERVER_SEQUENCE_NUM+1, synack_segment.seqnum+1, SegmentFlagType.ACK, ''.encode())
    sock.sendto(ack_segment.build(), addr)
    logging.info(f'Segment SEQ={synack_segment.seqnum}: Received {SegmentFlagType.getFlag(synack_segment.flagtype)}, Sent {SegmentFlagType.getFlag(ack_segment.flagtype_data)}')
    three_way_success = True
  else:
    logging.info(f'Received unknown flag! Retrying three way handshake..')

  return three_way_success

def send_data(sock: socket, f, client: tuple):
  # Read file
  seq_num = 0
  segments_to_send: List(Segment) = []
  while True:
    # Read data
    data = f.read(DATA_SIZE)
    if not data:
      break

    # Create data segment and add to list
    data_segment = Segment(SERVER_SEQUENCE_NUM+seq_num, 0, SegmentFlagType.DATA, data)
    seq_num += 1
    segments_to_send.append(data_segment)

  num_segments = len(segments_to_send)
  base = 0
  next_seq_num = SERVER_SEQUENCE_NUM
  # Sending data using Go-Back-N
  while base < num_segments:
    # Sb := 0
    # Sm := N + 1
    # Repeat the following steps forever:
    #   	if you receive an ack number where Rn > Sb then
    #       	Sm := (Sm − Sb) + Rn
    #       	Sb := Rn
    #   	if no packet is in transmission then
    #       	Transmit packets where Sb ≤ Sn ≤ Sm.  
    #       	Packets are transmitted in order.

    # Sent data segment in sliding windows
    while next_seq_num < min(base + WINDOW_SIZE, num_segments):
      sock.sendto(segments_to_send[next_seq_num].buffer, client)
      logging.info(f'Segment SEQ={next_seq_num}: Sent')
      next_seq_num += 1

    # Receive Ack segment from client
    valid, response_received, _ = listening_segment(sock, SegmentFlagType.ACK)
    if valid and response_received.acknum-1 == base:
      logging.info(f'Segment SEQ={base}: Packet Acked')
      
      base += 1
    else :
      logging.error(f'Segment SEQ={base}: Packet not acked! Sending all packet in sliding window..')

      # Sent data segment in sliding windows
      next_seq_num = base
      while next_seq_num < min(base + WINDOW_SIZE, num_segments):
        sock.sendto(segments_to_send[next_seq_num].buffer, client)
        logging.info(f'Segment SEQ={next_seq_num}: Sent')
        next_seq_num += 1

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
    # Listening for clients
    msg, addr = s.recvfrom(BUFFER_SIZE)

    if addr:
      # Add client address to list
      logging.info(f'Client {addr} found')
      client_list.append(addr)
      cont = input('Listen more? (y/n)')
    
      if cont == 'y':
        pass
      else:
        break

  logging.info(f'{len(client_list)} clients found:')
  for i in range(len(client_list)):
    logging.info(f'{i+1}. {client_list[i][0]}:{client_list[i][1]}')

  # Send message to all clients, perform three way handshake
  with open(FILE_PATH, 'rb') as f:

    for client in client_list:
      three_way_success = False
      try:
        three_way_success = three_way_handshake_server(s, client)
      except:
        logging.error(f'Error occured during three way handshake with client {client}!')

      if not three_way_success:
        logging.info(f'Client {client[0]}:{client[1]} fail to perform three way! Continuing sending data to other client..')
        continue
      
      logging.info('Three way success, sending data to client...')
      f.seek(0)
      try:
        send_data(s, f, client)
      except Exception as e:
        logging.error(f'Error occured during sending data to {client}')
        logging.error(e)
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
