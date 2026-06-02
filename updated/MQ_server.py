from socket import *
from utils import read_config
import select
import time
import random
import json

TOTAL_DURATION = 120  # 2분
TOTAL_CHUNKS = {
    "HQ": 45,
    "MQ": 30,
    "LQ": 15
}

class MQServer:
    def __init__(self):
        self.sock        = None
        self.quality     = 'MQ'
        self.streaming   = False
        self.client_addr = None
        self.chunks      = []
        self.chunk_idx   = 0
        self.next_send_time = 0


    def init(self):
        config = read_config('config.txt')
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.bind(config['MQ_server'])
        print(f'{self.quality} 스트리밍 서버 시작')

    def generate_chunks(self, video_index):
        chunks = []
        num_chunks     = TOTAL_CHUNKS[self.quality]
        chunk_duration = TOTAL_DURATION / num_chunks

        for i in range(num_chunks):
            chunks.append({
                "id" : video_index,
                "seq":        i,
                "start_time": round(i * chunk_duration, 3),
                "end_time":   round((i + 1) * chunk_duration, 3),
                "quality":    self.quality,
                "EOF":        i == num_chunks - 1
            })
        return chunks

    def find_start_idx(self, start_time):
        """start_time 이후 첫 번째 chunk index 반환"""
        for i, chunk in enumerate(self.chunks):
            if chunk['start_time'] >= start_time:
                return i
        return 0
    
    def make_random_delay(self):
        r = random.random()
        if r < 0.05:                          
            return time.time() + random.uniform(10,20)
        elif r < 0.35:
            return time.time() + random.uniform(5, 10)
        elif r < 0.95:                       
            return time.time() + random.uniform(0.5, 2)
        else:                                
            return time.time() + random.uniform(0.01, 0.1)

    def run(self):
        chunk_duration = TOTAL_DURATION / TOTAL_CHUNKS[self.quality]

        while True:
            readable, _, _ = select.select([self.sock], [], [], 0.1)

            if readable:
                data, addr = self.sock.recvfrom(4096)
                request    = json.loads(data.decode())
                print(f'스트리밍 요청 수신: {request} from {addr}')

                if request['type'] == 'start':
                    self.client_addr = addr
                    self.chunks      = self.generate_chunks(request['id'])
                    self.chunk_idx   = self.find_start_idx(request['start_time'])
                    self.streaming   = True
                    self.next_send_time = self.make_random_delay()
                    print(f'스트리밍 시작: {request["id"]} [{self.quality}]')

                elif request['type'] == 'stop':
                    self.streaming = False
                    print(f'스트리밍 중단')

            if self.streaming and self.chunk_idx < len(self.chunks) and time.time() >= self.next_send_time:
                chunk = self.chunks[self.chunk_idx]
                self.sock.sendto(json.dumps(chunk).encode(), self.client_addr)
                print(f'{self.chunk_idx} 번째 chunk 전송')
                self.chunk_idx += 1
                
                self.next_send_time = self.make_random_delay() 


            elif self.streaming and self.chunk_idx >= len(self.chunks):
                self.streaming = False
                print('스트리밍 완료')


if __name__ == '__main__':
    server = MQServer()
    server.init()
    server.run()