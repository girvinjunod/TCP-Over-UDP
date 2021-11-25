import sys
import socket
import logging
import time
from typing import List, Tuple
from segment import *
from segment_unwrapper import *

HOST = socket.gethostbyname(socket.gethostname())
SERVER_SEQUENCE_NUM = 0
BUFFER_SIZE = 32780
DATA_SIZE = 32768
WINDOW_SIZE = 64
TIMEOUT_DURATION = 5

def listening_segment(sock: socket, segment_type: SegmentFlagType) -> Tuple[bool, SegmentUnwrapper, tuple]:
  try:
    sock.settimeout(TIMEOUT_DURATION)
    msg, addr = sock.recvfrom(BUFFER_SIZE)
    sock.settimeout(None)
  except socket.timeout:
    logging.error(f'Segment timeout!')
    return False, None, None

  # Unwrap client message
  segment_received = SegmentUnwrapper(msg)

  # Check segment flag type
  if segment_received.flagtype == segment_type:
    return segment_received.is_valid, segment_received, addr

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
  elif synack_segment==None:
    logging.info(f'No response from client! Terminating connection..')
  else:
    logging.info(f'Received unknown flag! Retrying three way handshake..')

  return three_way_success

def send_data(sock: socket, f, client: tuple, file_metadata: str = None):
  # Read file
  seq_num = 0
  segments_to_send: List[Segment] = []

  # Add metadata segment
  if file_metadata:
    logging.info(f'Client require metadata, sending metadata as segment 0')
    segments_to_send.append(Segment(seq_num, 0, SegmentFlagType.DATA, file_metadata.encode()))
    seq_num += 1
  
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

    # Sent data segment in sliding windows
    while next_seq_num < min(base + WINDOW_SIZE, num_segments):
      sock.sendto(segments_to_send[next_seq_num].buffer, client)
      logging.info(f'Segment SEQ={next_seq_num}: Sent')
      next_seq_num += 1
      time.sleep(0.1)

    # Receive Ack segment from client
    valid, response_received, _ = listening_segment(sock, SegmentFlagType.ACK)
    if valid and response_received.acknum-1 == SERVER_SEQUENCE_NUM+base:
      logging.info(f'Segment SEQ={base}: Packet Acked')
      
      base += 1
    elif response_received.acknum - 1 > SERVER_SEQUENCE_NUM+base:
      base = response_received.acknum - 1
      logging.info(f'Segment SEQ={base}: Packet Acked')
    else :
      logging.error(f'Segment SEQ={base}: Packet not acked! Reset sliding window and resent all segment in window..')

      # Sent data segment in sliding windows
      next_seq_num = base

  # Send FIN segment to client
  fin_valid = False
  fin_segment = Segment(SERVER_SEQUENCE_NUM, 0, SegmentFlagType.FIN, b'')
  logging.info(f'All file segment is successfuly sent, sending Fin segment')
  while not fin_valid:
    sock.sendto(fin_segment.build(), client)

    # Receive Ack segment from client
    fin_valid, finack_segment, _ = listening_segment(sock, SegmentFlagType.FINACK)
    if fin_valid:
      logging.info(f'{SegmentFlagType.getFlag(finack_segment.flagtype)} Received, ending connection with {client[0]}:{client[1]}')
    else:
      logging.info(f'Client {client[0]}:{client[1]} fail to respond, retrying sending Fin segment..')

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
      if msg.decode() == 'Metadata required':
        logging.info(f'Client {addr} found, require metadata')
        client_list.append((addr, True))
      else:
        logging.info(f'Client {addr} found')
        client_list.append((addr, False))
      cont = input('Listen more? (y/n)')
    
      if cont == 'y':
        pass
      else:
        break

  logging.info(f'{len(client_list)} clients found:')
  for i in range(len(client_list)):
    logging.info(f'{i+1}. {client_list[i][0][0]}:{client_list[i][0][1]}')

  # Send message to all clients, perform three way handshake
  with open(FILE_PATH, 'rb') as f:

    for (client, metadata) in client_list:
      three_way_success = False
      while not three_way_success:
        try:
          three_way_success = three_way_handshake_server(s, client)
        except:
          logging.error(f'Error occured during three way handshake with client {client}!')

        if not three_way_success:
          logging.info(f'Client {client[0]}:{client[1]} fail to perform three way! Retrying..')
          continue

      logging.info('Three way success, sending data to client...')
      f.seek(0)
      try:
        if metadata:
          filename = FILE_PATH.split('/')[-1]
          send_data(s, f, client, filename)
        else:
          send_data(s, f, client)
      except Exception as e:
        logging.error(f'Error occured during sending data to {client}')
        logging.error(e)
        continue
  
  logging.info('Closing down server..')
  s.close()

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
