from socket import *
from utils import read_config
import select

video_index = {
    '1': 'https://index.netplus.com/12XP87QY',
    '2': 'https://index.netplus.com/AB34CDEF',
    '3': 'https://index.netplus.com/CD56EFGH',
    '4': 'https://index.netplus.com/EF78GHIJ',
    '5': 'https://index.netplus.com/GH90IJKL',
    '6': 'https://index.netplus.com/IJ12KLMN',
    '7': 'https://index.netplus.com/KL34MNOP',
    '8': 'https://index.netplus.com/MN56OPQR',
    '9': 'https://index.netplus.com/OP78QRST',
}

sock = socket(AF_INET, SOCK_DGRAM)
config = read_config('config.txt')
sock.bind(config['netplus_web_server'])
print('NetPlus Web Server 시작')

while True:
    readable, _, _ = select.select([sock], [], [], 0.1)
    if readable:
        data, addr = sock.recvfrom(1024)
        video_num = data.decode().strip()
        print(f'요청 수신: 영상 {video_num} from {addr}')

        index_url = video_index.get(video_num, None)
        if index_url:
            sock.sendto(index_url.encode(), addr)
            print(f'응답 전송: {index_url}')
        else:
            sock.sendto('ERROR'.encode(), addr)
        print()