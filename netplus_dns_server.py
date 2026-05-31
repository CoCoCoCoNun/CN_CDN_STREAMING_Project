from socket import *
import json
from utils import read_config
import select
records = {
    'https://index.netplus.com/12XP87QY': 'https://abCDN.net/mv984ctN770',
    'https://index.netplus.com/AB34CDEF': 'https://abCDN.net/bx731paK221',
    'https://index.netplus.com/CD56EFGH': 'https://abCDN.net/cx512qbL445',
    'https://index.netplus.com/EF78GHIJ': 'https://abCDN.net/dx293rcM668',
    'https://index.netplus.com/GH90IJKL': 'https://abCDN.net/ex074sdN891',
    'https://index.netplus.com/IJ12KLMN': 'https://abCDN.net/fx855teO114',
    'https://index.netplus.com/KL34MNOP': 'https://abCDN.net/gx636ufP337',
    'https://index.netplus.com/MN56OPQR': 'https://abCDN.net/hx417vgQ550',
    'https://index.netplus.com/OP78QRST': 'https://abCDN.net/ix198whR773',
}

class NetplusDNS:
    def __init__(self):
        self.sock       = None
    
    def init(self):
        self.sock = socket(AF_INET, SOCK_DGRAM)
        config = read_config('config.txt')
        self.sock.bind(config['netplus_dns_server'])
        
        print('Netplus DNS server 시작')
        
    def run(self):
        while True:
            readable, _, _ = select.select([self.sock], [], [], 0.1)

            if readable:
                data, client_addr = self.sock.recvfrom(4096)
                URL = data.decode()
                print(f'DNS query 수신: {URL} from {client_addr}')
                
                if URL in records:
                    abCDN_url = records[URL]
                
                response = {
                    "type": "referral",
                    "index_url": abCDN_url
                }
                print(f'DNS query 전송: {response} to {client_addr}')
                self.sock.sendto(json.dumps(response).encode(), client_addr)
            
if __name__ == '__main__':
    dns = NetplusDNS()
    dns.init()
    dns.run()