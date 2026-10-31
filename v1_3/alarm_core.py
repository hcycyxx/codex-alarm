"""Local scheduling and official Codex app-server transport. No UI automation."""
import ctypes
import datetime as dt
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import uuid

MODEL = 'gpt-6.1-sol'
TITLE = '定时唤醒'


class RpcServerError(RuntimeError):
    """An explicit server refusal, distinct from timeout/unknown outcome."""
    def __init__(self, error):
        self.error = error
        super().__init__(error.get('message', 'Codex 请求失败'))


def is_writer_conflict(error, thread_id):
    # Match only the known refusal for this exact thread, never arbitrary errors.
    return (isinstance(error, RpcServerError) and
            str(error).strip().lower() ==
            ('thread ' + thread_id + ' already has an active writer').lower())


def next_occurrence(hour, minute, now=None):
    now = now or dt.datetime.now()
    due = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
    return due if due > now else due + dt.timedelta(days=1)


class Store:
    """Append-only snapshots: a save never overwrites an earlier file."""
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def load(self):
        for file in sorted(self.root.glob('settings_*.json'), reverse=True):
            try:
                return json.loads(file.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                continue
        return {}

    def save(self, data):
        name = 'settings_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_' + uuid.uuid4().hex[:6] + '.json'
        with (self.root / name).open('x', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def log(self, text):
        name = 'event_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_' + uuid.uuid4().hex[:6] + '.txt'
        with (self.root / name).open('x', encoding='utf-8') as file:
            file.write(text)


def find_codex():
    # Prefer the newest installed desktop build, keeping its protocol in step.
    roots = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'WindowsApps'
    candidates = []
    try:
        for folder in roots.glob('OpenAI.Codex_*_x64__*'):
            exe = folder / 'app/resources/codex.exe'
            if exe.is_file():
                version = tuple(int(n) for n in folder.name.split('_')[1].split('.'))
                candidates.append((version, exe))
    except (OSError, ValueError):
        pass
    if candidates:
        return str(max(candidates)[1])
    npm = Path(os.environ.get('APPDATA', '')) / 'npm/node_modules/@openai/codex'
    if npm.exists():
        for exe in npm.rglob('codex.exe'):
            return str(exe)
    raise RuntimeError('没有找到 Codex。请先安装并登录 Codex 桌面软件。')


class Rpc:
    def __init__(self, executable=None):
        self.exe = executable or find_codex()
        self.proc = subprocess.Popen(
            [self.exe, 'app-server', '--stdio'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            encoding='utf-8', text=True, bufsize=1,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.pending = {}
        self.events = queue.Queue()
        self.lock = threading.Lock()
        self.serial = 0
        self.closed = False
        threading.Thread(target=self._reader, daemon=True).start()
        self.request('initialize', {
            'clientInfo': {'name': 'codex_alarm_v1', 'title': 'Codex 定时唤醒', 'version': '1.0.0'},
            'capabilities': {'experimentalApi': True}})
        self._write({'method': 'initialized'})

    def _write(self, data):
        with self.lock:
            self.proc.stdin.write(json.dumps(data, ensure_ascii=False) + '\n')
            self.proc.stdin.flush()

    def _reader(self):
        try:
            for line in self.proc.stdout:
                try:
                    data = json.loads(line)
                except ValueError:
                    continue
                if 'method' in data and 'id' in data:
                    # The sender never approves model tool operations unattended.
                    self._write({'id': data['id'], 'error': {
                        'code': -32601, 'message': '定时发送器不执行工具或授权操作。'}})
                elif 'id' in data:
                    target = self.pending.get(data['id'])
                    if target:
                        target.put(data)
                else:
                    self.events.put(data)
        finally:
            for target in list(self.pending.values()):
                target.put({'error': {'message': 'Codex 本机连接已断开；请查看聊天确认结果。'}})
            self.events.put({'method': '_disconnected'})

    def request(self, method, params, timeout=35):
        self.serial += 1
        key = self.serial
        target = queue.Queue()
        self.pending[key] = target
        try:
            self._write({'id': key, 'method': method, 'params': params})
            try:
                data = target.get(timeout=timeout)
            except queue.Empty:
                raise RuntimeError('Codex 响应超时。若已提交，请先查看聊天，避免重复发送。')
            if 'error' in data:
                raise RpcServerError(data['error'])
            return data.get('result', {})
        finally:
            self.pending.pop(key, None)

    def inspect(self):
        account = self.request('account/read', {}).get('account') or {}
        if account.get('type') != 'chatgpt':
            raise RuntimeError('请在 Codex 桌面软件中使用 ChatGPT 账号登录后再试。')
        models = self.request('model/list', {'limit': 100}).get('data', [])
        if not any(item.get('model') == MODEL for item in models):
            raise RuntimeError('当前账号没有提供 GPT-6.1 Sol。请先在 Codex 中确认模型。')
        # Confirms access to desktop history; never copies chat contents into logs.
        self.request('thread/list', {'limit': 1})
        return 'ChatGPT 已登录 · GPT-6.1 可用'

    def send(self, thread_id, text, workspace, on_thread, on_submitted, on_notice=None):
        self.inspect()
        common = {'model': MODEL, 'approvalPolicy': 'on-request', 'sandbox': 'read-only'}
        if thread_id:
            result = self.request('thread/read', {'threadId': thread_id, 'includeTurns': False})
            info = result['thread']
            if info.get('name') != TITLE:
                raise RuntimeError('绑定的聊天已改名。请先把聊天名称恢复为“定时唤醒”。')
            if info.get('status', {}).get('type') == 'active':
                raise RuntimeError('专用聊天正在运行，本次跳过。')
            try:
                self.request('thread/resume', dict(common, threadId=thread_id))
            except RpcServerError as error:
                if not is_writer_conflict(error, thread_id):
                    raise
                # resume carries no user input. A definite rejection here proves
                # that this attempt has not submitted the message anywhere.
                if on_notice:
                    on_notice('原专用聊天被桌面连接占用；本次尚未提交消息，将新建专用聊天。旧记录保留。')
                thread_id = ''
        if not thread_id:
            # Creating an empty thread is deferred until the user actually sends.
            Path(workspace).mkdir(parents=True, exist_ok=True)
            result = self.request('thread/start', dict(common, cwd=str(workspace),
                baseInstructions='这是定时消息专用聊天。请简短回答用户消息。不要调用工具、读取文件、执行命令或进行任何外部操作。',
                ephemeral=False))
            thread_id = result['thread']['id']
            on_thread(thread_id)  # Persist before naming/sending; no duplicate on retry.
            self.request('thread/name/set', {'threadId': thread_id, 'name': TITLE})
        result = self.request('turn/start', {
            'threadId': thread_id,
            'input': [{'type': 'text', 'text': text}],
            'model': MODEL, 'effort': 'low', 'approvalPolicy': 'on-request',
            'sandboxPolicy': {'type': 'readOnly'}})
        turn_id = result['turn']['id']
        on_submitted(thread_id, turn_id)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            try:
                event = self.events.get(timeout=1)
            except queue.Empty:
                continue
            if event.get('method') == '_disconnected':
                raise RuntimeError('消息已提交，但连接已断开。请查看专用聊天确认结果，不会自动重发。')
            params = event.get('params', {})
            if event.get('method') == 'turn/completed' and params.get('threadId') == thread_id:
                turn = params.get('turn', {})
                if turn.get('id') != turn_id:
                    continue
                if turn.get('status') != 'completed':
                    error = turn.get('error') or {}
                    raise RuntimeError('消息已提交，模型未完成：' + str(error.get('message', turn.get('status'))))
                return thread_id
        raise RuntimeError('消息已提交，等待回复超时。请查看专用聊天确认结果，不会自动重发。')

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.proc.stdin.close()
                self.proc.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()


def acquire_single_instance():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, 'Local\\JackCodexAlarmV1')
    if ctypes.windll.kernel32.GetLastError() == 183:
        return None
    return mutex
