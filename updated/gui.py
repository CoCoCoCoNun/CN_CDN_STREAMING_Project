import tkinter as tk
from tkinter import ttk
import threading

class StreamingGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NetPlus Streaming Client")
        self.root.geometry("700x500")
        self.root.configure(bg='#1a1a2e')
        self.root.resizable(False, False)

        self._build()

    def _build(self):
        # 타이틀
        tk.Label(self.root, text="NetPlus", font=('Courier', 24, 'bold'),
                 bg='#1a1a2e', fg='#e94560').pack(pady=(20, 0))
        tk.Label(self.root, text="Streaming Client", font=('Courier', 11),
                 bg='#1a1a2e', fg='#888').pack(pady=(0, 20))

        # 재생 정보
        self.status_var = tk.StringVar(value="대기 중...")
        tk.Label(self.root, textvariable=self.status_var,
                 font=('Courier', 13), bg='#1a1a2e', fg='#eee').pack()

        # 화질 표시
        self.quality_var = tk.StringVar(value="화질: -")
        tk.Label(self.root, textvariable=self.quality_var,
                 font=('Courier', 11), bg='#1a1a2e', fg='#e94560').pack(pady=5)

        # 재생 위치 바
        tk.Label(self.root, text="재생 위치", font=('Courier', 10),
                 bg='#1a1a2e', fg='#888').pack(pady=(15, 2))

        self.progress = ttk.Progressbar(self.root, length=500,
                                         mode='determinate', maximum=120)
        self.progress.pack()

        self.time_var = tk.StringVar(value="0.00s / 120.00s")
        tk.Label(self.root, textvariable=self.time_var,
                 font=('Courier', 9), bg='#1a1a2e', fg='#888').pack(pady=2)

        # 버퍼 바
        tk.Label(self.root, text="버퍼", font=('Courier', 10),
                 bg='#1a1a2e', fg='#888').pack(pady=(15, 2))

        self.buffer_bar = ttk.Progressbar(self.root, length=500,
                                           mode='determinate', maximum=10)
        self.buffer_bar.pack()

        self.buffer_var = tk.StringVar(value="0 / 10")
        tk.Label(self.root, textvariable=self.buffer_var,
                 font=('Courier', 9), bg='#1a1a2e', fg='#888').pack(pady=2)

        # buffer_rate
        self.rate_var = tk.StringVar(value="ROF: 0.000")
        tk.Label(self.root, textvariable=self.rate_var,
                 font=('Courier', 10), bg='#1a1a2e', fg='#16c79a').pack(pady=10)

        # 로그
        self.log_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.log_var,
                 font=('Courier', 9), bg='#1a1a2e', fg='#e94560').pack()

        # ttk 스타일
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TProgressbar", troughcolor='#16213e',
                        background='#e94560', thickness=18)
        
        self.status_label = tk.Label(self.root, textvariable=self.status_var,
                    font=('Courier', 13), bg='#1a1a2e', fg='#eee')
        self.status_label.pack()


    def update(self, current_time=None, quality=None,
               buffer_size=None, max_buffer=20,
               buffer_rate=None, status=None, log=None):
        """FSM에서 호출해서 UI 갱신"""
        def _update():
            if status is not None:  # None 체크로 변경 (빈 문자열도 표시)
                self.status_var.set(status)
                # 블랙아웃이면 빨간색, 아니면 흰색
                color = '#e94560' if 'Black Out' in status else '#eee'
                self.status_label.config(fg=color)
            if quality:
                self.quality_var.set(f"화질: {quality}")
            if current_time is not None:
                self.progress['value'] = current_time
                self.time_var.set(f"{current_time:.2f}s / 120.00s")
            if buffer_size is not None:
                self.buffer_bar['maximum'] = max_buffer
                self.buffer_bar['value']   = buffer_size
                self.buffer_var.set(f"{buffer_size} / {max_buffer}")
            if buffer_rate is not None:
                self.rate_var.set(f"ROF: {buffer_rate:.3f}")
            if log:
                self.log_var.set(log)

        self.root.after(0, _update)

    def start(self, fsm_run):
        """FSM을 별도 스레드로 실행하고 GUI 메인루프 시작"""
        t = threading.Thread(target=fsm_run, daemon=True)
        t.start()
        self.root.mainloop()
