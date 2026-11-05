"""Offline regression checks for the three reported window issues. No RPC."""
import ctypes as C
import json
from pathlib import Path
import tempfile
import traceback
import time
import tkinter as tk
from PIL import ImageGrab
from alarm_core import Store
from codex_alarm_v1_7 import GlassApp


def check():
    root=tk.Tk()
    errors=[]
    def fail(*error):
        errors.append(str(error))
        traceback.print_exception(*error)
        root.destroy()
    root.report_callback_exception=fail
    app=GlassApp(root,preview=True)
    stamp=time.strftime('%Y%m%d_%H%M%S')
    def snapshot(name):
        ImageGrab.grab(window=root.winfo_id()).save(Path(__file__).parent/f'{name}_{stamp}.png')
    app.begin_send=lambda:(_ for _ in ()).throw(AssertionError('unexpected send'))
    root.update()
    app.apply_plan(12,10)
    assert len(app.slot_buttons)==len(app.slot_checks)==len(app.slots)==5
    assert not hasattr(app,'plan_page')
    texts=[app.canvas.itemcget(i,'text') for i in app.canvas.find_all() if app.canvas.type(i)=='text']
    assert not any(text in ('上一页','下一页') for text in texts)
    try:app.apply_plan(12,10)
    except ValueError:pass
    else:raise AssertionError('duplicate accepted')

    # Exercise the actual header event handlers, including screen pointer offsets.
    left,top,right,bottom=app.chrome.rectangle()
    app.header.event_generate('<Button-1>',x=200,y=60,rootx=left+200,rooty=top+60)
    assert app.chrome.pointer_operation
    app.header.event_generate('<B1-Motion>',x=272,y=90,rootx=left+272,rooty=top+90)
    app.header.event_generate('<ButtonRelease-1>',x=272,y=90)
    root.update()
    moved=app.chrome.rectangle()
    assert moved[0]==left+72 and moved[1]==top+30,(moved,(left,top,right,bottom))
    assert app.chrome.pointer_operation is None

    # The caption cannot be re-added by a style update during activation.
    u=app.chrome.u
    u.SendMessageW.argtypes=[C.c_void_p,C.c_uint,C.c_size_t,C.c_ssize_t]
    u.SendMessageW.restype=C.c_ssize_t
    style=app.chrome.get_long(app.chrome.hwnd,-16)
    app.chrome.set_long(app.chrome.hwnd,-16,style|0x00C00000)
    assert not app.chrome.get_long(app.chrome.hwnd,-16)&0x00C00000
    assert u.SendMessageW(app.chrome.hwnd,0x0086,0,0)==1
    assert not app.chrome.get_long(app.chrome.hwnd,-16)&0x00C00000
    root.geometry('900x1010+10+10')

    def tall():
        root.update()
        snapshot('preview_five_plans_tall')
        left,top,right,bottom=app.chrome.rectangle()
        app.chrome.begin_pointer((left+right)//2,bottom-2,'b')
        app.chrome.move_pointer((left+right)//2,bottom-222)
        app.chrome.end_pointer()
        root.update()
        new=app.chrome.rectangle()
        assert new[3]-new[1]<bottom-top
        root.geometry('790x620+10+10')
        root.after(350,short)

    def short():
        root.update()
        assert app.canvas.winfo_height()<900
        assert app.content_height>app.canvas.winfo_height()
        assert app.scrollbar.winfo_ismapped()
        event=type('WheelEvent',(),{'delta':-120})()
        app.scroll_wheel(event)
        app.reveal_slot(4)
        root.update()
        assert app.canvas.yview()[0]>0
        switch=app.slot_checks[4]
        x=(switch.bounds[0]+switch.bounds[2])/2
        y=(switch.bounds[1]+switch.bounds[3])/2-app.canvas.canvasy(0)
        assert y>app.header.winfo_height()
        app.canvas.event_generate('<Button-1>',x=int(x),y=int(y))
        assert not app.slot_vars[4].get()  # Correct hit testing after scrolling.
        snapshot('preview_short_scrolled')
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);store.save(app.settings())
            assert len(store.load()['slots'])==5
            assert not store.load()['slots'][4][2]
        # Switch to another window belonging to this check, then capture inactive app.
        dummy=tk.Toplevel(root)
        dummy.title('本地焦点检查')
        dummy.geometry('180x80+1050+40')
        dummy.focus_force()
        root.after(350,lambda:inactive(dummy))

    def inactive(dummy):
        root.update()
        assert not app.chrome.get_long(app.chrome.hwnd,-16)&0x00C00000
        assert u.SendMessageW(app.chrome.hwnd,0x0085,0,0)==0
        snapshot('preview_inactive')
        dummy.destroy()
        app.chrome.minimize();root.update()
        app.chrome.u.ShowWindow(app.chrome.hwnd,9);root.update()
        app.chrome.maximize();root.update()
        assert app.chrome.u.IsZoomed(app.chrome.hwnd)
        app.chrome.maximize();root.update()
        app.remove_plans(range(5))
        assert app.next_due(app.beijing_now()) is None and not app.plan_remove.enabled
        assert not errors,errors
        print(json.dumps({'offline_checks':'passed','real_messages_sent':0,
            'checked':['all five rows','no pagination','header pointer drag','height resize',
                       'short-window scroll','scrolled switch hit target','inactive caption suppression',
                       'focus switch','minimize/restore','maximize/restore','settings','empty plans']}))
        root.destroy()

    root.after(400,tall)
    root.mainloop()
    assert not errors,errors


if __name__=='__main__':check()
