"""Native tray regression checks. No RPC or actual model messages."""
import ctypes as C
import datetime as dt
import json
from pathlib import Path
import time
import tkinter as tk
import traceback
from PIL import ImageGrab
from codex_alarm_v1_8 import GlassApp


def check():
    root=tk.Tk()
    errors=[]
    def failed(*error):
        errors.append(str(error))
        traceback.print_exception(*error)
        root.destroy()
    root.report_callback_exception=failed
    app=GlassApp(root,preview=True)
    root.update()
    stamp=time.strftime('%Y%m%d_%H%M%S')
    original=[slot[:] for slot in app.slots]
    ui_ticks=[]
    simulated_sends=[]
    app.begin_send=lambda:simulated_sends.append('simulated only')
    assert not app.active and not app.tray.registered
    assert len(app.slots)==4
    assert any(kind=='tray' for _,kind in app.header_buttons)
    app.chrome.u.SendMessageW.argtypes=[C.c_void_p,C.c_uint,C.c_size_t,C.c_ssize_t]
    app.chrome.u.SendMessageW.restype=C.c_ssize_t

    def start():
        # Exercise the new header button, rather than calling only its helper.
        bounds=next(bounds for bounds,kind in app.header_buttons if kind=='tray')
        x,y=(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2
        left,top,_,_=app.chrome.rectangle()
        app.header.event_generate('<Button-1>',x=int(x),y=int(y),rootx=int(left+x),rooty=int(top+y))
        assert app.tray.registered and app.tray.hidden
        assert not app.tray.u.IsWindowVisible(app.chrome.hwnd)
        assert not app.active and '已暂停' in app.tray.tip
        # Hiding never arms a paused plan. With an armed plan the same Tk timer
        # loop must survive SW_HIDE and reach the existing scheduling callback.
        app.active=True
        app.due=app.beijing_now()-dt.timedelta(seconds=1)
        app.last_attempt=''
        root.after(120,lambda:ui_ticks.append('timer while hidden'))
        root.after(550,restored)

    def restored():
        assert ui_ticks and len(simulated_sends)==1
        assert app.active and app.tray.hidden
        assert app.slots==original
        # Deliver the same native callback Windows sends for double click.
        app.chrome.u.SendMessageW(app.chrome.hwnd,app.tray.CALLBACK,0,(1<<16)|0x0203)
        root.after(250,visible)

    def visible():
        assert not app.tray.hidden and not app.tray.registered
        assert app.tray.u.IsWindowVisible(app.chrome.hwnd)
        assert app.active and app.slots==original
        assert not app.chrome.get_long(app.chrome.hwnd,-16)&0x00C00000
        app.chrome.maximize();root.update()
        assert app.chrome.u.IsZoomed(app.chrome.hwnd)
        app.hide_to_tray()
        assert app.tray.registered and app.tray.was_zoomed
        # Simulate Explorer losing its icons, without restarting Explorer.
        app.tray.remove_icon()
        app.chrome.u.SendMessageW(app.chrome.hwnd,app.tray.taskbar_message,0,0)
        root.after(250,recovered)

    def recovered():
        assert app.tray.registered and app.tray.hidden
        app.tray.command(app.tray.RESTORE)
        root.after(250,menu_restored)

    def menu_restored():
        assert not app.tray.registered and not app.tray.hidden
        assert app.chrome.u.IsZoomed(app.chrome.hwnd)
        app.chrome.maximize();root.update()
        app.active=False
        app.set_status('已暂停 · 不会自动发送',False)
        root.geometry('790x700+10+10')
        root.after(350,screenshot)

    def screenshot():
        root.update()
        assert any(kind=='tray' for _,kind in app.header_buttons)
        ImageGrab.grab(window=root.winfo_id()).save(Path(__file__).parent/f'preview_tray_button_{stamp}.png')
        app.hide_to_tray()
        app.tray.command(app.tray.EXIT)

    root.after(350,start)
    root.mainloop()
    assert app.tray.closed and not app.tray.registered
    assert not errors,errors
    print(json.dumps({'offline_checks':'passed','real_messages_sent':0,
        'checked':['header hide button','native icon creation','paused stays paused',
                   'Tk timers while hidden','scheduled callback with simulated send only',
                   'double-click notification restores','maximized state restores',
                   'taskbar icon recovery','menu show command','menu exit command',
                   'icon cleanup','old caption stays suppressed','plans unchanged']}))


if __name__=='__main__':check()
