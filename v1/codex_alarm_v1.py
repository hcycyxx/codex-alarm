import datetime as dt
import math
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox

from alarm_core import MODEL, Rpc, Store, acquire_single_instance, next_occurrence

BG = '#f5f5f7'
INK = '#1d1d1f'
MUTED = '#64646b'
BLUE = '#0071e3'
FONT = 'Microsoft YaHei UI'


class RoundedFrame(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # Native Tk content with four small quarter-circle corners.
        for rx, ry, anchor, bbox, start in (
            (0, 0, 'nw', (0, 0, 32, 32), 90),
            (1, 0, 'ne', (-16, 0, 16, 32), 0),
            (0, 1, 'sw', (0, -16, 32, 16), 180),
            (1, 1, 'se', (-16, -16, 16, 16), 270)):
            corner = tk.Canvas(self, width=16, height=16, bg=BG, bd=0, highlightthickness=0)
            corner.create_arc(*bbox, start=start, extent=90, fill='white', outline='white')
            px, py = int(kwargs.get('padx', 0)), int(kwargs.get('pady', 0))
            corner.place(relx=rx, rely=ry, anchor=anchor,
                         x=px if rx else -px, y=py if ry else -py)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, primary=False):
        self.label, self.command, self.primary = text, command, primary
        self.enabled, self.hover, self.focused = True, False, False
        super().__init__(parent, width=138 if primary else 119, height=43,
                         bg=BG, highlightthickness=0, bd=0, takefocus=True, cursor='hand2')
        self.bind('<ButtonRelease-1>', self.invoke)
        self.bind('<Return>', self.invoke)
        self.bind('<space>', self.invoke)
        self.bind('<Enter>', lambda e: self.highlight(True))
        self.bind('<Leave>', lambda e: self.highlight(False))
        self.bind('<FocusIn>', lambda e: self.focus(True))
        self.bind('<FocusOut>', lambda e: self.focus(False))
        self.bind('<Configure>', lambda e: self.draw())
        self.draw()

    def configure(self, **kwargs):
        if 'text' in kwargs:
            self.label = kwargs.pop('text')
        if 'state' in kwargs:
            self.enabled = kwargs.pop('state') != 'disabled'
        if kwargs:
            super().configure(**kwargs)
        self.draw()

    def draw(self):
        self.delete('all')
        w, h = int(self.cget('width')), int(self.cget('height'))
        color = (('#005ebd' if self.hover else BLUE) if self.primary else
                 ('#dcdce3' if self.hover else '#e8e8ed')) if self.enabled else '#e1e1e6'
        r = 11
        points = [r, 1, w-r, 1, w-1, 1, w-1, r, w-1, h-r, w-1, h-1,
                  w-r, h-1, r, h-1, 1, h-1, 1, h-r, 1, r, 1, 1]
        self.create_polygon(points, smooth=True, splinesteps=16, fill=color,
                            outline=BLUE if self.focused else '', width=2)
        self.create_text(w/2, h/2, text=self.label,
            fill=('white' if self.primary else INK) if self.enabled else '#686871',
            font=(FONT, 10, 'bold' if self.primary else 'normal'))

    def highlight(self, value):
        self.hover = value
        self.draw()

    def focus(self, value):
        self.focused = value
        self.draw()

    def invoke(self, event=None):
        if self.enabled:
            self.focus_set()
            self.command()
        return 'break'


class Wheel(tk.Canvas):
    def __init__(self, parent, count, value, changed, label):
        super().__init__(parent, width=118, height=204, bg='white', bd=0,
                         highlightthickness=0, takefocus=True, cursor='hand2')
        self.count, self.value, self.changed = count, int(value), changed
        self.offset, self.velocity, self.y0 = 0., 0., 0
        self.anim = None
        self.label = label
        self.bind('<MouseWheel>', self.scroll)
        self.bind('<ButtonPress-1>', self.press)
        self.bind('<B1-Motion>', self.drag)
        self.bind('<ButtonRelease-1>', self.release)
        self.bind('<Up>', lambda e: self.step(-1))
        self.bind('<Down>', lambda e: self.step(1))
        self.bind('<FocusIn>', lambda e: self.draw())
        self.bind('<FocusOut>', lambda e: self.draw())
        self.bind('<Configure>', lambda e: self.draw())
        self.draw()

    def draw(self):
        self.delete('all')
        w, h = max(118, self.winfo_width()), max(204, self.winfo_height())
        cy = h / 2
        self.create_rectangle(4, cy-26, w-4, cy+26, fill='#f1f1f4', outline='')
        for i in range(-3, 4):
            y = cy + i*48 + self.offset
            distance = abs(y-cy)
            if y < -10 or y > h+10:
                continue
            color = INK if distance < 25 else '#77777f' if distance < 74 else '#a0a0a7'
            size = 36 if distance < 25 else 27 if distance < 74 else 21
            self.create_text(w/2, y, text=f'{(self.value+i)%self.count:02}',
                             fill=color, font=('Segoe UI', size, 'normal'))
        if self.focus_get() == self:
            self.create_line(16, cy+28, w-16, cy+28, fill=BLUE, width=2)

    def step(self, delta):
        if self.anim:
            self.after_cancel(self.anim)
        self.value = (self.value + delta) % self.count
        self.offset = 35. * (1 if delta > 0 else -1)
        self.changed()
        self.settle()
        return 'break'

    def settle(self):
        self.offset *= .64
        if abs(self.offset) < .4:
            self.offset = 0
            self.anim = None
        else:
            self.anim = self.after(16, self.settle)
        self.draw()

    def scroll(self, event):
        self.focus_set()
        return self.step(-1 if event.delta > 0 else 1)

    def press(self, event):
        self.focus_set()
        if self.anim:
            self.after_cancel(self.anim)
            self.anim = None
        self.y0 = self.last_y = event.y
        self.offset = 0

    def drag(self, event):
        self.offset += event.y-self.last_y
        self.last_y = event.y
        while self.offset >= 48:
            self.value = (self.value-1) % self.count
            self.offset -= 48
            self.changed()
        while self.offset <= -48:
            self.value = (self.value+1) % self.count
            self.offset += 48
            self.changed()
        self.draw()

    def release(self, event):
        if abs(event.y-self.y0) < 5:
            row = round((event.y-self.winfo_height()/2)/48)
            if row:
                self.step(row)
                return
        if abs(self.offset) > 24:
            self.value = (self.value + (-1 if self.offset > 0 else 1)) % self.count
            self.changed()
        self.settle()


class App:
    def __init__(self, root, preview=False):
        self.root, self.preview = root, preview
        data_dir = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'CodexAlarm/v1'
        self.store = Store(data_dir)
        saved = {} if preview else self.store.load()
        self.thread_id = saved.get('thread_id', '')
        self.last_attempt = saved.get('last_attempt', '')
        self.active, self.busy, self.due = False, False, None
        self.results = queue.Queue()
        self.rpc = None
        root.title('Codex 定时唤醒 · V1')
        root.geometry('860x860')
        root.minsize(760, 820)
        root.configure(bg=BG)
        root.option_add('*Font', (FONT, 10))
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.body = tk.Frame(root, bg=BG)
        self.body.pack(fill='both', expand=True, padx=34, pady=(23, 20))
        header = tk.Frame(self.body, bg=BG)
        header.pack(fill='x')
        self.text(header, '定时唤醒', 25, bold=True).pack(side='left')
        self.text(header, 'Codex  /  V1.0', 10, MUTED).pack(side='right', pady=(12, 0))
        self.text(self.body, '让一条消息，准时出发。', 11, MUTED).pack(anchor='w', pady=(5, 22))

        schedule = RoundedFrame(self.body, bg='white', padx=24, pady=17)
        schedule.pack(fill='x')
        top = tk.Frame(schedule, bg='white')
        top.pack(fill='x')
        self.text(top, '发送时间', 12, bold=True, bg='white').pack(side='left')
        self.repeat = tk.BooleanVar(value=saved.get('repeat', True))
        self.check = tk.Checkbutton(top, text='每天重复', variable=self.repeat, bg='white',
            fg=MUTED, activebackground='white', selectcolor='white', bd=0,
            command=self.edit)
        self.check.pack(side='right')
        wheels = tk.Frame(schedule, bg='white')
        wheels.pack(pady=(0, 0))
        self.hour = Wheel(wheels, 24, saved.get('hour', 5), self.edit, '小时')
        self.hour.pack(side='left')
        self.text(wheels, ':', 30, INK, bg='white').pack(side='left', padx=8)
        self.minute = Wheel(wheels, 60, saved.get('minute', 0), self.edit, '分钟')
        self.minute.pack(side='left')
        self.text(schedule, '24 小时制 · 滚动、拖动或使用上下方向键', 9, MUTED, bg='white').pack()

        self.next_label = self.text(self.body, '', 11)
        self.next_label.pack(anchor='w', pady=(15, 6))
        self.countdown = self.text(self.body, '尚未开启定时', 10, MUTED)
        self.countdown.pack(anchor='w', pady=(0, 19))

        message_head = tk.Frame(self.body, bg=BG)
        message_head.pack(fill='x')
        self.text(message_head, '发送内容', 12, bold=True).pack(side='left')
        self.text(message_head, 'GPT-6.1 Sol  ·  专用聊天“定时唤醒”', 9, MUTED).pack(side='right')
        editor_frame = RoundedFrame(self.body, bg='white', padx=15, pady=12)
        editor_frame.pack(fill='x', pady=(10, 0))
        self.editor = tk.Text(editor_frame, height=3, wrap='word', bg='white', fg=INK,
            insertbackground=BLUE, selectbackground='#cde5ff', relief='flat', undo=True,
            font=(FONT, 11), bd=0, highlightthickness=0, padx=0, pady=0)
        self.editor.pack(fill='x')
        self.editor.insert('1.0', saved.get('message', '只回复 OK。'))
        self.editor.bind('<<Modified>>', self.message_changed)
        self.editor.edit_modified(False)
        self.text(self.body, '电脑需保持开机并联网；最小化后继续计时，关闭程序则停止。',
                  9, MUTED).pack(anchor='w', pady=(9, 16))

        actions = tk.Frame(self.body, bg=BG)
        actions.pack(fill='x')
        self.arm = self.button(actions, '开启定时', self.toggle, primary=True)
        self.arm.pack(side='left')
        self.send = self.button(actions, '立即试发…', self.send_now)
        self.send.pack(side='left', padx=10)
        self.check_btn = self.button(actions, '检查连接', self.check_connection)
        self.check_btn.pack(side='right')

        status_frame = tk.Frame(self.body, bg=BG)
        status_frame.pack(fill='x', pady=(19, 7))
        self.dot = self.text(status_frame, '●', 11, '#86868b')
        self.dot.pack(side='left')
        self.status = self.text(status_frame, '已暂停 · 不会自动发送', 10, MUTED)
        self.status.pack(side='left', padx=7)
        self.logs_btn = self.text(status_frame, '查看记录', 9, BLUE)
        self.logs_btn.configure(cursor='hand2')
        self.logs_btn.pack(side='right')
        self.logs_btn.bind('<Button-1>', lambda e: self.open_logs())
        self.history = tk.Text(self.body, height=3, bg=BG, fg=MUTED, wrap='word',
            font=(FONT, 9), bd=0, highlightthickness=0, state='disabled', takefocus=False)
        self.history.pack(fill='both', expand=True)
        self.refresh_next()
        self.add_log('准备就绪。先检查连接，再开启定时或立即试发。', persist=False)
        root.after(300, self.tick)
        root.after(100, self.poll)

    def text(self, parent, value, size=10, color=INK, bold=False, bg=BG):
        return tk.Label(parent, text=value, bg=bg, fg=color,
                        font=(FONT, size, 'bold' if bold else 'normal'), anchor='w')

    def button(self, parent, value, command, primary=False):
        return RoundedButton(parent, value, command, primary)

    def settings(self):
        return {'hour': self.hour.value, 'minute': self.minute.value,
            'repeat': self.repeat.get(), 'message': self.editor.get('1.0', 'end-1c').strip(),
            'thread_id': self.thread_id, 'last_attempt': self.last_attempt}

    def save(self):
        if not self.preview:
            self.store.save(self.settings())

    def message_changed(self, event=None):
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        self.edit()

    def edit(self):
        if not hasattr(self, 'minute') or not hasattr(self, 'editor'):
            return
        if self.active:
            self.active = False
            self.arm.configure(text='开启定时')
            self.set_status('设置已修改 · 请重新开启定时', False)
        self.refresh_next()

    def refresh_next(self):
        now = dt.datetime.now()
        upcoming = self.due if self.active else next_occurrence(self.hour.value, self.minute.value, now)
        day = '今天' if upcoming.date() == now.date() else '明天' if upcoming.date() == (now+dt.timedelta(days=1)).date() else upcoming.strftime('%m 月 %d 日')
        self.next_label.configure(text=f'下次发送  {day} {upcoming:%H:%M}  ·  '+('每天' if self.repeat.get() else '仅一次'))

    def set_status(self, text, active=None):
        self.status.configure(text=text)
        self.dot.configure(fg=BLUE if (self.active if active is None else active) else '#86868b')

    def add_log(self, text, persist=True):
        line = f'{dt.datetime.now():%m-%d %H:%M:%S}  {text}'
        self.history.configure(state='normal')
        self.history.insert('1.0', line+'\n')
        self.history.configure(state='disabled')
        if persist and not self.preview:
            try:
                self.store.log(line)
            except OSError:
                self.set_status('记录保存失败，请检查磁盘空间', False)

    def toggle(self):
        if self.active:
            self.active = False
            self.arm.configure(text='开启定时')
            self.set_status('已暂停 · 不会自动发送', False)
            self.countdown.configure(text='尚未开启定时')
            return
        if not self.editor.get('1.0', 'end-1c').strip():
            messagebox.showinfo('请填写内容', '先写好要发送给 Codex 的消息。', parent=self.root)
            return
        try:
            self.save()
        except OSError as exc:
            messagebox.showerror('无法保存设置', str(exc), parent=self.root)
            return
        self.due = next_occurrence(self.hour.value, self.minute.value)
        self.active = True
        self.arm.configure(text='暂停定时')
        self.set_status('定时已开启 · 到点自动发送', True)
        self.add_log(f'已开启：{self.due:%m-%d %H:%M}；'+('每天重复。' if self.repeat.get() else '仅发送一次。'))
        self.refresh_next()

    def tick(self):
        if self.active:
            now = dt.datetime.now()
            seconds = (self.due-now).total_seconds()
            if seconds <= 0:
                occurrence = self.due.isoformat()
                late = -seconds
                if self.repeat.get():
                    self.due = next_occurrence(self.hour.value, self.minute.value, now)
                else:
                    self.active = False
                    self.arm.configure(text='开启定时')
                if late > 120:
                    self.add_log('本次错过超过 2 分钟，已跳过；不会在唤醒电脑后突然补发。')
                elif self.busy:
                    self.add_log('本次到点时仍在发送上一条，已跳过，避免重复。')
                elif occurrence != self.last_attempt:
                    self.last_attempt = occurrence
                    try:
                        self.save()  # Durable attempt marker before model submission.
                    except OSError:
                        self.active = False
                        self.arm.configure(text='开启定时')
                        self.set_status('无法保存运行记录 · 已暂停', False)
                    else:
                        self.begin_send()
                self.refresh_next()
            else:
                n = math.ceil(seconds)
                self.countdown.configure(text=f'距离发送还有 {n//3600:02}:{n//60%60:02}:{n%60:02}')
        elif not self.busy:
            self.countdown.configure(text='尚未开启定时')
        self.root.after(300, self.tick)

    def send_now(self):
        text = self.editor.get('1.0', 'end-1c').strip()
        if not text:
            messagebox.showinfo('请填写内容', '先写好要发送的消息。', parent=self.root)
            return
        if messagebox.askokcancel('确认发送给 Codex',
            '即将使用 GPT-6.1 Sol，在专用“定时唤醒”聊天真实发送：\n\n'+text+'\n\n这会使用当前登录账号的模型额度。是否发送？', parent=self.root):
            self.begin_send()

    def begin_send(self):
        if self.busy or self.preview:
            return
        try:
            self.save()
        except OSError as exc:
            messagebox.showerror('无法保存设置', str(exc), parent=self.root)
            return
        snapshot = self.settings()
        self.busy = True
        self.controls(False)
        self.set_status('正在连接 Codex…', True)
        self.add_log('开始连接；暂未确认消息提交。')

        def work():
            rpc = None
            try:
                rpc = Rpc()
                self.rpc = rpc
                def remember(thread_id):
                    # Worker cannot access Tk; save using the captured snapshot.
                    snapshot['thread_id'] = thread_id
                    self.store.save(snapshot)
                    self.results.put(('thread', thread_id))
                def submitted(thread_id, turn_id):
                    self.results.put(('submitted', turn_id))
                thread_id = rpc.send(snapshot['thread_id'], snapshot['message'],
                    self.store.root / 'workspace', remember, submitted)
                self.results.put(('done', thread_id))
            except Exception as exc:
                self.results.put(('error', str(exc)))
            finally:
                if rpc:
                    rpc.close()
                self.rpc = None
        threading.Thread(target=work, daemon=True).start()

    def controls(self, enabled):
        state = 'normal' if enabled else 'disabled'
        for button in (self.send, self.check_btn, self.arm, self.check):
            button.configure(state=state)
        self.editor.configure(state=state)
        # Wheels cannot edit the active plan while its message is in flight.
        for wheel in (self.hour, self.minute):
            wheel.configure(state='normal' if enabled else 'disabled')
            wheel.unbind('<MouseWheel>') if not enabled else wheel.bind('<MouseWheel>', wheel.scroll)
            wheel.unbind('<ButtonPress-1>') if not enabled else wheel.bind('<ButtonPress-1>', wheel.press)
            wheel.unbind('<B1-Motion>') if not enabled else wheel.bind('<B1-Motion>', wheel.drag)
            wheel.unbind('<ButtonRelease-1>') if not enabled else wheel.bind('<ButtonRelease-1>', wheel.release)
            wheel.unbind('<Up>') if not enabled else wheel.bind('<Up>', lambda e, w=wheel: w.step(-1))
            wheel.unbind('<Down>') if not enabled else wheel.bind('<Down>', lambda e, w=wheel: w.step(1))

    def check_connection(self):
        if self.busy or self.preview:
            return
        self.busy = True
        self.controls(False)
        self.set_status('正在检查连接 · 不会发送消息', True)
        def work():
            rpc = None
            try:
                rpc = Rpc()
                self.results.put(('checked', rpc.inspect()))
            except Exception as exc:
                self.results.put(('error', str(exc)))
            finally:
                if rpc:
                    rpc.close()
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, payload = self.results.get_nowait()
                if kind == 'thread':
                    self.thread_id = payload
                elif kind == 'submitted':
                    self.set_status('消息已提交 · 等待模型完成', True)
                    self.add_log('Codex 已确认接收消息；等待模型回复。')
                elif kind == 'done':
                    self.thread_id = payload
                    self.busy = False
                    self.controls(True)
                    self.set_status('发送完成 · GPT-6.1 已回复')
                    self.add_log('发送完成。可在 Codex 的“定时唤醒”聊天中查看。')
                elif kind == 'checked':
                    self.busy = False
                    self.controls(True)
                    self.set_status(payload)
                    self.add_log('连接检查通过；没有发送消息。')
                elif kind == 'error':
                    self.busy = False
                    self.controls(True)
                    self.set_status('本次未完成 · 请查看记录')
                    self.add_log(payload[:1000])
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def open_logs(self):
        if not self.preview:
            os.startfile(str(self.store.root))

    def close(self):
        if self.busy:
            messagebox.showinfo('请稍等', 'Codex 正在处理，请等本次结束后再关闭。', parent=self.root)
            return
        if self.active and not messagebox.askokcancel('关闭后停止定时',
            '关闭程序后不会定时发送。\n如需继续计时，请取消并使用右上角最小化。', parent=self.root):
            return
        try:
            self.save()
        except OSError:
            pass
        self.root.destroy()


def main():
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    preview = '--preview' in sys.argv
    mutex = acquire_single_instance()
    if not mutex:
        ctypes.windll.user32.MessageBoxW(None, '程序已经打开，请查看任务栏。', 'Codex 定时唤醒', 0)
        return
    root = tk.Tk()
    App(root, preview=preview)
    root.mainloop()


if __name__ == '__main__':
    main()
