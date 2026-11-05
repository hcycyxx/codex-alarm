"""Small offline checks. Preview mode cannot send or save user settings."""
import ctypes
import datetime as dt
import json
from pathlib import Path
import tempfile
import tkinter as tk
from PIL import ImageGrab
from alarm_core import Store
from codex_alarm_v1_6 import GlassApp


def check():
    root=tk.Tk()
    errors=[]
    root.report_callback_exception=lambda *error:errors.append(str(error))
    app=GlassApp(root,preview=True)
    root.update()
    # Any accidental transport entry is a check failure; never create an RPC client.
    app.begin_send=lambda:(_ for _ in ()).throw(AssertionError('unexpected send'))
    assert len(app.slots)==4 and not app.active
    app.apply_plan(23,15)
    assert len(app.slots)==5 and len(app.slot_buttons)==1 and app.plan_page==1
    assert app.next_due(dt.datetime(2026,11,5,20,0))==dt.datetime(2026,11,5,23,15)
    try:app.apply_plan(23,15)
    except ValueError:pass
    else:raise AssertionError('duplicate schedule accepted')
    app.turn_page(-1)
    assert len(app.slot_buttons)==4 and app.plan_page==0
    # Editing a later-page item must update that exact global index.
    app.apply_plan(22,30,4)
    assert app.slots[4][:2]==[22,30]
    app.slot_vars[4].set(False)
    assert app.next_due(dt.datetime(2026,11,5,20,0))==dt.datetime(2026,11,6,4,50)
    # Shared persistence supports an arbitrary count, disabled slots and empty lists.
    with tempfile.TemporaryDirectory() as folder:
        store=Store(folder)
        store.save(app.settings())
        assert len(store.load()['slots'])==5 and not store.load()['slots'][4][2]
    app.remove_plans(range(len(app.slots)))
    assert app.slots==[] and app.slot_vars==[] and app.next_due(dt.datetime.now()) is None
    assert not app.plan_remove.enabled
    for hour,minute in [(4,50),(9,51),(14,52),(19,53)]:app.apply_plan(hour,minute)
    app.active=True
    app.apply_plan(22,30)
    assert not app.active  # Changed plans require explicit re-arming.
    app.remove_plans([4])
    app.slot_vars[0].set(False)
    root.geometry('790x900');root.update()
    assert not app.slot_vars[0].get() and len(app.slots)==4
    assert app.chrome.get_long(app.chrome.hwnd,-16)&0x00C00000==0
    assert app.chrome.get_long(app.chrome.hwnd,-20)&0x00040000
    app.chrome.minimize();root.update()
    app.chrome.u.ShowWindow(app.chrome.hwnd,9);root.update()
    assert not app.active
    app.slot_vars[0].set(True)

    def screenshots():
        try:
            root.update()
            ImageGrab.grab(window=root.winfo_id()).save(Path(__file__).parent/'preview_minimum_final.png')
            root.geometry('1044x1000+10+10')
            root.after(450,large)
        except Exception:
            root.destroy();raise

    def large():
        root.update()
        assert app.chrome.region_size[0]>=root.winfo_width()
        assert app.chrome.region_size[1]>=root.winfo_height()
        ImageGrab.grab(window=root.winfo_id()).save(Path(__file__).parent/'preview_large_final.png')
        app.apply_plan(22,30)
        app.apply_plan(23,15)
        root.after(250,multiple)

    def multiple():
        root.update()
        ImageGrab.grab(window=root.winfo_id()).save(Path(__file__).parent/'preview_more_plans_final.png')
        assert not errors,errors
        print(json.dumps({'offline_checks':'passed','real_messages_sent':0,
                          'checks':['add','duplicate rejection','pagination','edit later item',
                                    'disabled schedule','snapshot persistence','delete all','re-arm',
                                    'borderless taskbar window','minimize/restore','resize']},ensure_ascii=False))
        root.destroy()

    root.after(500,screenshots)
    root.mainloop()


if __name__=='__main__':check()
