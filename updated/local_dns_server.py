from socket import *
import json
from utils import read_config
import select

class LocalDNS:
    def __init__(self):
        self.sock    = None
        self.cache          = {}
        
    
    def init(self):
        config = read_config('config.txt')
        self.cache['netplus.com'] = config['netplus_dns_server'] #정확히는 netplus.com의 NS 와 ns1.netplus.com의 A record
        self.cache['abCDN.net'] = config['abCDN_dns_server'] #정확히는 abCDN.net의 NS 와 ns1.abCDN.net의 A record
        
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.bind(config['local_dns_server'])
        
        print('Local DNS 서버 시작')

    #dns를 suffix로 records에 있는지 검사
    def find_dns(self, domain):
        print(f'{domain}의 record를 cache에서 검색합니다.')
        parts = domain.split('.')
        for i in range(len(parts)):
            candidate = '.'.join(parts[i:])
            if candidate in self.cache:
                print(f'suffix가 가장 많이 일치하는 records를 찾았습니다. {candidate} : {self.cache[candidate]}')
                return self.cache[candidate]
        
    def iterative_query(self, dns, index_url):
        next_dns = dns
        query = index_url

        while True:
            print()
            print(f'DNS query 전송: {index_url} to {next_dns}')
            self.sock.sendto(query.encode(), next_dns)
            data, _ = self.sock.recvfrom(4096)
            response = json.loads(data.decode())

            if response['type'] == 'answer':
                print(f'DNS response 수신: {response} from {next_dns}')
                print(f'manifest 파일을 획득하였습니다.')
                print()
                return response['manifest']
            elif response['type'] == 'referral':
                print(f'DNS refferal 수신: {response} from {next_dns} ')
                query    = response['index_url']
                domain = query.replace("https://", "").split('/')[0]
                next_dns = self.find_dns(domain)
                index_url = query
                print(f'추가 질의를 전송합니다...')
            else:
                return None
            
    def run(self):
        while True:
            data, client_addr = self.sock.recvfrom(4096)
            query = data.decode()
            domain = query.replace("https://", "").split('/')[0]
            
            print(f'DNS query 수신: {query} from {client_addr}')
            
            dns = self.find_dns(domain)
            print()
            print(f'iterative query 시작')
            manifest = self.iterative_query(dns, query)
            
            self.sock.sendto(json.dumps(manifest).encode(), client_addr)
            print(f'DNS response 전송: {manifest} to {client_addr}')
            
           


if __name__ == '__main__':
    dns = LocalDNS()
    dns.init()
    dns.run()