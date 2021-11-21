import sys
import socket
import logging
from segment import *

HOST = socket.gethostbyname(socket.gethostname())
SERVER_SEQUENCE_NUM = 1
BUFFER_SIZE = 8208*4
DATA_SIZE = 32768

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
      if segment_received.flagtype == SegmentFlagType.ACK and segment_received.acknum == response_segment.seqnum_data+1:
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
  with open(FILE_PATH, 'rb') as f:
    # Read data
    # filename = f.name.split('/')[-1]

    for client in client_list:
      f.seek(0)
      data_sent = 0
      while True:
        data = f.read(DATA_SIZE)
        if not data:
          break

        # Send file name
        # filename_segment = Segment(SERVER_SEQUENCE_NUM, 0, SegmentFlagType.DATA, filename.encode())
        # s.sendto(filename_segment.build(), client)
        # SERVER_SEQUENCE_NUM += 1

        # Send file
        segment_to_send = Segment(SERVER_SEQUENCE_NUM+data_sent, 0, SegmentFlagType.DATA, data)
        s.sendto(segment_to_send.build(), client)
        logging.info(f'Segment SEQ={segment_to_send.seqnum_data}: Sent')
        data_sent += 1

      data_received = 0
      while data_received < data_sent:
        msg, addr = s.recvfrom(BUFFER_SIZE)
        response_received = SegmentUnwrapper(msg)
        if response_received.flagtype == SegmentFlagType.ACK:
          logging.info(f'Segment SEQ={response_received.acknum-1}: Packet Acked')
        else:
          logging.error(f'Segment SEQ={response_received.acknum-1}: Packet not acked')
        data_received += 1
      
      fin_segment = Segment(SERVER_SEQUENCE_NUM, 0, SegmentFlagType.FIN, b'')
      s.sendto(fin_segment.build(), client)
      logging.info(f'File successfuly sent to {client}')

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
