"""Windows notification icon using the app's existing UI thread and HWND."""
import ctypes as C
from ctypes import wintypes as W


class GUID(C.Structure):
    _fields_=[('data1',W.DWORD),('data2',W.WORD),('data3',W.WORD),('data4',W.BYTE*8)]


class NOTIFYICONDATA(C.Structure):
    _fields_=[('cbSize',W.DWORD),('hWnd',W.HWND),('uID',W.UINT),('uFlags',W.UINT),
        ('uCallbackMessage',W.UINT),('hIcon',W.HICON),('szTip',W.WCHAR*128),
        ('dwState',W.DWORD),('dwStateMask',W.DWORD),('szInfo',W.WCHAR*256),
        ('uVersion',W.UINT),('szInfoTitle',W.WCHAR*64),('dwInfoFlags',W.DWORD),
        ('guidItem',GUID),('hBalloonIcon',W.HICON)]


class POINT(C.Structure):
    _fields_=[('x',W.LONG),('y',W.LONG)]


class TrayIcon:
    CALLBACK=0x8000+90
    RESTORE=1
    EXIT=2

    def __init__(self,root,chrome,icon_path,on_restore,on_exit):
        self.root,self.chrome,self.hwnd=root,chrome,chrome.hwnd
        self.on_restore,self.on_exit=on_restore,on_exit
        self.u,self.shell=C.windll.user32,C.windll.shell32
        self.shell.Shell_NotifyIconW.argtypes=[W.DWORD,C.POINTER(NOTIFYICONDATA)]
        self.shell.Shell_NotifyIconW.restype=W.BOOL
        self.u.LoadImageW.argtypes=[W.HINSTANCE,W.LPCWSTR,W.UINT,C.c_int,C.c_int,W.UINT]
        self.u.LoadImageW.restype=W.HANDLE
        self.u.LoadIconW.argtypes=[W.HINSTANCE,C.c_void_p]
        self.u.LoadIconW.restype=W.HICON
        self.u.DestroyIcon.argtypes=[W.HICON]
        self.u.RegisterWindowMessageW.argtypes=[W.LPCWSTR]
        self.u.RegisterWindowMessageW.restype=W.UINT
        self.u.IsWindowVisible.argtypes=[W.HWND]
        self.u.IsWindowVisible.restype=W.BOOL
        self.u.SetForegroundWindow.argtypes=[W.HWND]
        self.u.CreatePopupMenu.restype=W.HMENU
        self.u.AppendMenuW.argtypes=[W.HMENU,W.UINT,C.c_size_t,W.LPCWSTR]
        self.u.TrackPopupMenu.argtypes=[W.HMENU,W.UINT,C.c_int,C.c_int,C.c_int,W.HWND,C.c_void_p]
        self.u.TrackPopupMenu.restype=W.UINT
        self.u.DestroyMenu.argtypes=[W.HMENU]
        self.u.GetCursorPos.argtypes=[C.POINTER(POINT)]
        self.u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM]
        self.icon=self.u.LoadImageW(None,str(icon_path),1,32,32,0x10)
        self.own_icon=bool(self.icon)
        if not self.icon:self.icon=self.u.LoadIconW(None,C.c_void_p(32512))
        self.registered=False
        self.hidden=False
        self.closed=False
        self.was_zoomed=False
        self.version4=False
        self.tip='Codex 定时唤醒 · 已暂停'
        self.taskbar_message=self.u.RegisterWindowMessageW('TaskbarCreated')
        chrome.message_handlers[self.CALLBACK]=self._notification
        chrome.message_handlers[self.taskbar_message]=self._taskbar_created
        root.bind('<Destroy>',self._destroy,add='+')

    def _data(self):
        data=NOTIFYICONDATA()
        data.cbSize=C.sizeof(data)
        data.hWnd=self.hwnd
        data.uID=1
        data.uFlags=0x01|0x02|0x04|0x80  # callback, icon, tooltip, show tooltip
        data.uCallbackMessage=self.CALLBACK
        data.hIcon=self.icon
        data.szTip=self.tip[:127]
        return data

    def ensure_icon(self):
        if self.closed:raise RuntimeError('托盘已经退出。')
        if self.registered:return
        data=self._data()
        if not self.shell.Shell_NotifyIconW(0,C.byref(data)):
            raise RuntimeError('无法添加托盘图标，窗口保持显示。请稍后再试。')
        self.registered=True
        data.uVersion=4
        self.version4=bool(self.shell.Shell_NotifyIconW(4,C.byref(data)))

    def update_tip(self,text):
        self.tip=text[:127]
        if self.registered:
            data=self._data()
            if not self.shell.Shell_NotifyIconW(1,C.byref(data)):
                self.registered=False
                if self.hidden:self._enqueue(self._recover)

    def hide_window(self):
        # Never hide unless Windows has confirmed the recovery icon exists.
        self.ensure_icon()
        if self.hidden:return
        self.was_zoomed=bool(self.u.IsZoomed(self.hwnd))
        self.chrome.end_pointer()
        self.hidden=True
        self.u.ShowWindow(self.hwnd,0)

    def restore_window(self):
        self.hidden=False
        self.u.ShowWindow(self.hwnd,3 if self.was_zoomed else 9)
        self.u.SetForegroundWindow(self.hwnd)
        self.remove_icon()

    def remove_icon(self):
        if self.registered:
            self.shell.Shell_NotifyIconW(2,C.byref(self._data()))
            self.registered=False

    def _enqueue(self,action):
        if not self.closed:
            self.root.after(0,lambda:action() if not self.closed else None)

    def _notification(self,hwnd,msg,wparam,lparam):
        if self.closed:return 0
        if self.version4 and (lparam>>16)&0xffff != 1:return 0
        event=lparam&0xffff
        if event in (0x0202,0x0203,0x0400,0x0401):
            self._enqueue(self.on_restore)
        elif event in (0x007b,0x0205):
            self._enqueue(self.show_menu)
        return 0

    def command(self,identifier):
        if identifier==self.RESTORE:self._enqueue(self.on_restore)
        elif identifier==self.EXIT:self._enqueue(self.on_exit)

    def show_menu(self):
        if self.closed or not self.registered:return
        menu=self.u.CreatePopupMenu()
        if not menu:return
        try:
            self.u.AppendMenuW(menu,0,self.RESTORE,'显示窗口')
            self.u.AppendMenuW(menu,0x0800,0,None)
            self.u.AppendMenuW(menu,0,self.EXIT,'退出程序')
            point=POINT()
            self.u.GetCursorPos(C.byref(point))
            self.u.SetForegroundWindow(self.hwnd)
            result=self.u.TrackPopupMenu(menu,0x0100|0x0002,point.x,point.y,0,self.hwnd,None)
        finally:
            self.u.DestroyMenu(menu)
            self.u.PostMessageW(self.hwnd,0,0,0)
        if result:self.command(result)

    def _recover(self):
        try:self.ensure_icon()
        except RuntimeError:self.on_restore()

    def _taskbar_created(self,hwnd,msg,wparam,lparam):
        self.registered=False
        if self.hidden:self._enqueue(self._recover)
        return 0

    def stop(self):
        if self.closed:return
        self.remove_icon()
        self.closed=True
        self.chrome.message_handlers.pop(self.CALLBACK,None)
        self.chrome.message_handlers.pop(self.taskbar_message,None)
        if self.own_icon and self.icon:
            self.u.DestroyIcon(self.icon)
            self.icon=None

    def _destroy(self,event):
        if event.widget is self.root:self.stop()
