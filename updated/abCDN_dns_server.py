from socket import *
import json
from utils import read_config
import select

config = read_config('config.txt')
HQ_server = config['HQ_server']
MQ_server = config['MQ_server']
LQ_server = config['LQ_server']
records = {
    'https://abCDN.net/mv984ctN770': {"HQ": HQ_server , "MQ": MQ_server, "LQ": LQ_server},
    'https://abCDN.net/bx731paK221': {"HQ": HQ_server , "MQ": MQ_server, "LQ": LQ_server},
    'https://abCDN.net/cx512qbL445': {"HQ": HQ_server , "MQ": MQ_server, "LQ": LQ_server},
    'https://abCDN.net/dx293rcM668': {"HQ": HQ_server , "MQ": MQ_server, "LQ": LQ_server},
    'https://abCDN.net/ex074sdN891': {"HQ": HQ_server , "MQ": MQ_server, "LQ": LQ_server},
    'https://abCDN.net/fx855teO114': {"HQ": HQ_server , "MQ": MQ_server, "LQ": LQ_server},
    'https://abCDN.net/gx636ufP337': {"HQ": HQ_server , "MQ": MQ_server, "LQ": LQ_server},
    'https://abCDN.net/hx417vgQ550': {"HQ": HQ_server , "MQ": MQ_server, "LQ": LQ_server},
    'https://abCDN.net/ix198whR773': {"HQ": HQ_server , "MQ": MQ_server, "LQ": LQ_server}
}
class abCDN_DNS:
    def __init__(self):
        self.sock           = None
        self.cache          = {}
    def init(self):
        self.cache['netplus.com'] = config['netplus_dns_server']
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.bind(config['abCDN_dns_server'])
        print('abCDN DNS server 시작')
        
    def run(self):
        while True:
            readable, _, _ = select.select([self.sock], [], [], 0.1)

            if readable: 
                manifest = '' #심각한 버그! 초기화하지 않으면 이전 응답을 반환함
                data, client_addr = self.sock.recvfrom(4096)
                query = data.decode()
                print(f'DNS query 수신: {query} from {client_addr}')
                
                if query in records:
                    manifest = records[query]
                
                response = {
                    "type": "answer",
                    "manifest": manifest
                }
                
                print(f'DNS reponse 전송: {response} to {client_addr}')
                self.sock.sendto(json.dumps(response).encode(), client_addr)
                print()
            
if __name__ == '__main__':
    dns = abCDN_DNS()
    dns.init()
    dns.run()