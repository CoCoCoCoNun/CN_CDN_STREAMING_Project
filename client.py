#client.py

from socket import *
from enum import Enum, auto
import heapq
import select
import threading
import time
import json
from utils import read_config
from gui import StreamingGUI


Q = ['LQ', 'MQ', 'HQ']
K = 5
ONE_PROBE_TIME = 0.5
EWMA_WEIGHT = 0.6
QUALITY_UP = 0.7
QUALITY_DOWN = 0.2
STARTING_CONDITION = 0.6


class State(Enum):
    INIT                = auto()
    WAIT_USER_SELECT    = auto()
    WAIT_VIDEO_INDEX    = auto()
    WAIT_MANIFEST      = auto()
    INIT_BUFFER         = auto()
    STREAMING           = auto()
    WAIT_QUALITY_CHANGE = auto()
    END_STREAMING       = auto()
    ERROR               = auto()
    

class ClientFSM:
    def __init__(self,gui):
        self.gui = gui  # GUI 주입

        self.state = State.INIT
        
        self.config         = {}
        self.sock           = None
        
        self.selected_video = None
        self.video_index    = None
        self.manifest       = None
        self.buffer = []
        self.MAX_BUFFER     = None
        self.buffer_rate    = 0
        self.quality        = Q[2]
        self.before_quality = Q[2]
        self.current_chunk  = None
        self.requested      = False
        self.play_thread    = None
        self.quality_down   = None
         

    def run(self):
        while True:
            if self.state == State.INIT:
                self.handle_init()
            elif self.state == State.WAIT_USER_SELECT:
                self.handle_wait_user_select()
            elif self.state == State.WAIT_VIDEO_INDEX:
                self.handle_wait_video_index()
            elif self.state == State.WAIT_MANIFEST:
                self.handle_wait_manifest()
            elif self.state == State.INIT_BUFFER:
                self.handle_init_buffer()
            elif self.state == State.STREAMING:
                self.handle_streaming()
            elif self.state == State.WAIT_QUALITY_CHANGE:
                self.handle_wait_quality_change()
            elif self.state == State.END_STREAMING:
                self.handle_end_streaming()
            
            
            
    #INIT: 소켓을 생성.
    def handle_init(self):
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.config = read_config('config.txt')
        self.sock.bind(self.config['client'])
        
        self.state = State.WAIT_USER_SELECT
        return
    
    #WAIT_USER_SELECT: 사용자로부터 시청할 동영상 정보 받기.
    def handle_wait_user_select(self):
        self.selected_video = input('시청할 동영상을 선택하세요(1~9):')
        
        self.state = State.WAIT_VIDEO_INDEX
        return
    
    #WAIT_VIDEO_INDEX: 해당 동영상의 URL 받아오기.
    def handle_wait_video_index(self):
        self.sock.sendto(self.selected_video.encode(), self.config['netplus_web_server'])
        response, _= self.sock.recvfrom(1024)
        self.video_index = response.decode()
        
        self.state = State.WAIT_MANIFEST
        return

    #WAIT_MANIFEST: 해당 동영상의 manifest 파일 받아오기.
    def handle_wait_manifest(self):
        self.sock.sendto(self.video_index.encode(), self.config['local_dns_server'])
        response, _ = self.sock.recvfrom(1024)
        
        data = json.loads(response.decode())
        data = {k: tuple(v) for k, v in data.items()}
        self.manifest = data
        print(self.manifest)
        
        self.state = State.INIT_BUFFER
        return

    #INIT_BUFFER: 버퍼 초기화 및 스트리밍 요청
    def handle_init_buffer(self):
        if not self.requested:
            request = {
                "id" : self.selected_video,
                "start_time": 0,
                "type" : "start"
            }
            self.sock.sendto(json.dumps(request).encode(), self.manifest[self.quality])
            self.requested = True
        
        self.MAX_BUFFER = 5
        self.probe_buffer()
        
        if (len(self.buffer) >= STARTING_CONDITION * self.MAX_BUFFER):
            self.state = State.STREAMING   
        
        return
        
   #STREAMING: 스트리밍 시작(최초 재생 스레드 시작) 및 probe와 화질 전환 검사
    def handle_streaming(self):
        # 재생 스레드 시작 (한 번만)
        if self.play_thread is None or not self.play_thread.is_alive():
            self.play_thread = threading.Thread(target=self._play_loop)
            self.play_thread.daemon = True
            self.play_thread.start()

        # 메인은 probe + check만
        while self.state == State.STREAMING:
            self.probe_buffer()
            self.check_probe()
            if self.state == State.WAIT_QUALITY_CHANGE:
                self.handle_wait_quality_change()
                print(f'품질 전환 완료 buffer: {len(self.buffer)}') 
                self.state = State.STREAMING

    #별도의 스레드에서 스트리밍을 진행시키는 재생 루프
    def _play_loop(self):
        """백그라운드 재생 루프"""
        while self.state not in (State.END_STREAMING, State.ERROR):
            if len(self.buffer) == 0:
                self.gui.update(status='⚠ Black Out')  # GUI에 표시
                time.sleep(0.1)
                continue

            _, _, self.current_chunk = heapq.heappop(self.buffer)
            chunk = self.current_chunk
            print(f'재생: seq={chunk["seq"]} EOF={chunk["EOF"]}')  # 추가

            duration   = chunk['end_time'] - chunk['start_time']
            start_time = chunk['start_time']
            quality    = chunk['quality']
            video_id   = chunk['id']

            elapsed = 0
            interval = 0.05
            while elapsed < duration:
                self.gui.update(
                    status=f'▶ 영상 {video_id} 재생 중',
                    current_time=start_time + elapsed,
                    quality=quality,
                    buffer_size=len(self.buffer),
                    max_buffer=self.MAX_BUFFER,
                )
                time.sleep(interval)
                elapsed += interval
            
            
            if (self.current_chunk['EOF']):
                self.state = State.END_STREAMING

    #WAIT_QUALITY_CHANGE: 화질 전환이 감지되면, 화질 전환을 수행하고 전환이 완료되면 STREAMING으로 돌아감.
    def handle_wait_quality_change(self):
        # 1. 새 화질 요청
        self.before_quality = self.quality
        before_quality_index = Q.index(self.quality)
        if self.quality_down: self.quality = Q[before_quality_index - 1]
        else: self.quality = Q[before_quality_index + 1]
        print(f'새 화질을 요청합니다. {self.before_quality} -> {self.quality}')
        
        
        self.gui.update(log=f'화질 전환: {self.before_quality} → {self.quality}')
        
        end_time = self.current_chunk['end_time']
        stop_msg = json.dumps({"type": "stop"}).encode()
        self.sock.sendto(stop_msg, self.manifest[self.before_quality])

        start_msg = json.dumps({"type": "start", "id": self.selected_video, "start_time": end_time}).encode()
        self.sock.sendto(start_msg, self.manifest[self.quality])

        # 2. 새 청크 수신 대기
        new_chunk = None
        while new_chunk is None:
            readable, _, _ = select.select([self.sock], [], [], 0.1)
            if readable:
                data, addr = self.sock.recvfrom(1024)
                if(addr == self.manifest[self.before_quality]): 
                    chunk = json.loads(data.decode())  
                    heapq.heappush(self.buffer, (chunk['start_time'], chunk['end_time'], chunk))
                    continue
                if(addr == self.manifest[self.quality]):
                    new_chunk = json.loads(data.decode())
                
            # 3. new_chunk start_time > current_chunk end_time 인지 확인
            if new_chunk is not None and new_chunk['start_time'] > end_time:
                self.buffer = [c for c in self.buffer if c[1] <= new_chunk['start_time']]
                heapq.heapify(self.buffer)
                heapq.heappush(self.buffer, (new_chunk['start_time'], new_chunk['end_time'], new_chunk))  
                self.state = State.STREAMING
                return
            else:
                new_chunk = None
    
    #END_STREAMING: 영상 시청이 완료되면, 소켓과 config를 제외한 속성을 초기화하고 WAIT_USER_SELECT로 돌아감
    def handle_end_streaming(self):
        self.selected_video = None
        self.video_index    = None
        self.manifest       = None
        self.buffer = []
        self.MAX_BUFFER     = None
        self.buffer_rate    = 0
        self.quality        = Q[2]
        self.before_quality = Q[2]
        self.current_chunk  = None
        self.requested      = False
        self.play_thread    = None
        self.quality_down   = None
        
        print('스트리밍 종료.')
        print('초기화면으로 돌아갑니다.')
        print()
        self.gui.update(
            status='대기 중...',
            quality='-',
            current_time=0,
            buffer_size=0,
            buffer_rate=0,
            log=f''
        )
        
        self.state = State.WAIT_USER_SELECT
        
    def handle_error(self):
        pass
        
    def probe_buffer(self):
        for _ in range(K):
            if len(self.buffer) >= self.MAX_BUFFER:  # 버퍼 가득 차면 스킵
                break
            readable, _, _ = select.select([self.sock], [], [], ONE_PROBE_TIME)
            if readable:
                data, _ = self.sock.recvfrom(4096)
                chunk = json.loads(data.decode())
                heapq.heappush(self.buffer, (chunk['start_time'], chunk['end_time'], chunk))

        
        if self.state == State.INIT_BUFFER and self.buffer_rate == 0:
            self.buffer_rate = len(self.buffer) / self.MAX_BUFFER  # 첫 번째 probe → 바로 설정
        else:
            self.buffer_rate = EWMA_WEIGHT * self.buffer_rate + (1-EWMA_WEIGHT) * len(self.buffer) / self.MAX_BUFFER  # 이후 EWMA        
        self.gui.update(
            buffer_size=len(self.buffer),
            buffer_rate=self.buffer_rate,
            max_buffer=self.MAX_BUFFER
        )
    
    def check_probe(self):
        print(f'buffer_rate: {self.buffer_rate:.3f} quality: {self.quality} buffer: {len(self.buffer)}')

        if (self.buffer_rate < QUALITY_DOWN and self.quality != 'LQ'):
            self.quality_down = True
            self.state = State.WAIT_QUALITY_CHANGE
        if (self.buffer_rate >= QUALITY_UP and self.quality != 'HQ'):
            self.quality_down = False
            self.state = State.WAIT_QUALITY_CHANGE
        
            
if __name__ == '__main__':
    gui = StreamingGUI()
    client = ClientFSM(gui)
    gui.start(client.run)