"""Liquid-glass presentation; scheduling and transport reused from V1.3."""
import ctypes
import os
import queue
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFilter, ImageTk
from alarm_base import App as BaseApp, Wheel
from alarm_core import Store, acquire_single_instance

INK = '#17243b'
MUTED = '#52617a'
BLUE = '#0065d8'
FONT = 'Microsoft YaHei UI'


def rounded(canvas, bounds, radius, **options):
    x,y,x2,y2=bounds
    r=radius
    return canvas.create_polygon(x+r,y,x2-r,y,x2,y,x2,y+r,x2,y2-r,
        x2,y2,x2-r,y2,x+r,y2,x,y2,x,y2-r,x,y+r,x,y,
        smooth=True,splinesteps=24,**options)


class CanvasText:
    def __init__(self, canvas, x, y, text='', size=14, color=INK, bold=False, anchor='w'):
        self.canvas=canvas
        self.item=canvas.create_text(x,y,text=text,fill=color,anchor=anchor,
            font=(FONT,-size,'bold' if bold else 'normal'))

    def configure(self, **options):
        mapped={('fill' if key=='fg' else key): value for key,value in options.items()
                if key in ('text','fg','fill')}
        self.canvas.itemconfigure(self.item,**mapped)


class Action(CanvasText):
    def __init__(self, app, bounds, text, command, size=14, primary=False, anchor='center'):
        self.app,self.command,self.enabled,self.bounds=app,command,True,bounds
        self.primary=primary
        x,y,x2,y2=bounds
        self.hit=app.canvas.create_rectangle(*bounds,fill='',outline='')
        super().__init__(app.canvas,(x+x2)/2 if anchor=='center' else x,(y+y2)/2,
                         text,size,'#ffffff' if primary else INK,primary,anchor)
        for item in (self.item,self.hit):
            app.canvas.tag_bind(item,'<Enter>',lambda e:app.canvas.configure(cursor='hand2' if self.enabled else ''))
            app.canvas.tag_bind(item,'<Leave>',lambda e:app.canvas.configure(cursor=''))
        app.actions.append(self)

    def configure(self, **options):
        if 'state' in options:
            self.enabled=options.pop('state')!='disabled'
            options['fg']=('#ffffff' if self.primary else INK) if self.enabled else '#7b8799'
        super().configure(**options)

    def invoke(self):
        if self.enabled:
            self.command()


class Switch:
    def __init__(self,app,x,y,var,command):
        self.app,self.canvas,self.x,self.y=app,app.canvas,x,y
        self.var,self.command,self.enabled=var,command,True
        self.position=1. if var.get() else 0.
        self.tag='switch_'+str(id(self))
        self.timer=None
        app.actions.append(self)
        self.bounds=(x-3,y-3,x+57,y+33)
        self.draw()

    def draw(self):
        c=self.canvas;x=self.x;y=self.y
        c.delete(self.tag)
        track='#31bd70' if self.var.get() and self.enabled else '#bac6d5'
        c.create_line(x+15,y+15,x+39,y+15,fill=track,width=30,capstyle='round',tags=self.tag)
        cx=x+15+24*self.position
        c.create_oval(cx-12,y+4,cx+12,y+28,fill='#699c86' if self.var.get() else '#9ca9b9',outline='',tags=self.tag)
        c.create_oval(cx-12,y+3,cx+12,y+27,fill='white',outline='#edf2f6',tags=self.tag)
        c.tag_bind(self.tag,'<Enter>',lambda e:c.configure(cursor='hand2' if self.enabled else ''))
        c.tag_bind(self.tag,'<Leave>',lambda e:c.configure(cursor=''))

    def invoke(self):
        if not self.enabled:return
        self.var.set(not self.var.get())
        self.command()
        self.animate()

    def animate(self):
        if self.timer:self.canvas.after_cancel(self.timer)
        target=1. if self.var.get() else 0.
        self.position+=(target-self.position)*.4
        if abs(target-self.position)<.02:
            self.position=target;self.timer=None
        else:self.timer=self.canvas.after(16,self.animate)
        self.draw()

    def configure(self, **options):
        if 'state' in options:self.enabled=options['state']!='disabled'
        self.draw()


def glass_background(width,height,left,right):
    # Refraction and blur of this application's own background, not the desktop.
    w,h=max(1,width//3),max(1,height//3)
    base=Image.new('RGB',(w,h),'#e5edf7')
    layer=Image.new('RGBA',(w,h));d=ImageDraw.Draw(layer)
    d.ellipse((-w*.4,-h*.25,w*.65,h*.55),fill=(115,186,255,190))
    d.ellipse((w*.4,-h*.2,w*1.5,h*.7),fill=(207,171,249,165))
    d.ellipse((-w*.25,h*.65,w*.8,h*1.5),fill=(129,212,223,135))
    d.ellipse((w*.7,h*.5,w*1.4,h*1.2),fill=(255,212,184,135))
    base=Image.alpha_composite(base.convert('RGBA'),layer.filter(ImageFilter.GaussianBlur(65)))
    base=base.resize((width,height),Image.Resampling.BICUBIC)
    for bounds,radius in [((left,126,right,410),28),((left,428,right,497),23),
                          ((left,516,right,646),25),((left,666,left+160,714),24),
                          ((left+176,666,left+312,714),24),((right-136,666,right,714),24)]:
        x,y,x2,y2=map(int,bounds)
        shadow=Image.new('RGBA',base.size);sd=ImageDraw.Draw(shadow)
        sd.rounded_rectangle((x+1,y+8,x2+1,y2+10),radius,fill=(67,87,126,25))
        base=Image.alpha_composite(base,shadow.filter(ImageFilter.GaussianBlur(12)))
        mask=Image.new('L',(x2-x,y2-y));md=ImageDraw.Draw(mask)
        md.rounded_rectangle((0,0,x2-x-1,y2-y-1),radius,fill=255)
        refracted=base.crop((x,y,x2,y2)).filter(ImageFilter.GaussianBlur(10))
        refracted=Image.blend(refracted,Image.new('RGBA',refracted.size,'white'),.56)
        if y==666 and x==left:
            refracted=Image.blend(refracted,Image.new('RGBA',refracted.size,'#0075ed'),.93)
        base.paste(refracted,(x,y),mask)
        edge=ImageDraw.Draw(base)
        edge.rounded_rectangle((x,y,x2-1,y2-1),radius,outline=(255,255,255,220),width=1)
        edge.arc((x+2,y+2,x+radius*2,y+radius*2),180,270,fill='white',width=2)
        edge.line((x+radius,y+1,x2-radius,y+1),fill=(255,255,255,245),width=2)
    return base


class GlassApp(BaseApp):
    def __init__(self,root,preview=False):
        self.root,self.preview=root,preview
        parent=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'CodexAlarm'
        saved={}
        if not preview:
            for version in ('v1_4','v1_3','v1'):
                folder=parent/version
                if folder.exists():
                    saved=Store(folder).load()
                    if saved:break
        self.store=Store(parent/'v1_4')
        self.slots=saved.get('slots',[[4,50,True],[9,51,True],[14,52,True],[19,53,True]])
        self.thread_id=saved.get('thread_id','')
        self.last_attempt=saved.get('last_attempt','')
        self.active,self.busy,self.due=False,False,None
        self.busy_kind=None;self.results=queue.Queue();self.rpc=None
        self.slot_vars=[tk.BooleanVar(value=s[2]) for s in self.slots]
        self.repeat=tk.BooleanVar(value=True)
        self.check=tk.Checkbutton(root,variable=self.repeat)
        self.hour=Wheel(root,24,4,self.edit,'小时')
        self.minute=Wheel(root,60,50,self.edit,'分钟')
        root.title('Codex 定时唤醒 · V1.4')
        root.geometry('900x860');root.minsize(790,840)
        root.configure(bg='#e5edf7')
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.canvas=tk.Canvas(root,bd=0,highlightthickness=0,bg='#e5edf7',takefocus=True)
        self.canvas.pack(fill='both',expand=True)
        self.editor=tk.Text(root,wrap='word',height=2,bg='#f1f5fc',fg=INK,
            font=(FONT,-15),bd=0,highlightthickness=0,insertbackground=BLUE,
            selectbackground='#b9d9ff',undo=True,padx=6,pady=5)
        self.editor.insert('1.0',saved.get('message','只回复 OK。'))
        self.editor.edit_modified(False)
        self.editor.bind('<<Modified>>',self.message_changed)
        self.history=tk.Text(root,bg='#e3edf8',fg=MUTED,wrap='word',height=2,
            font=(FONT,-12),bd=0,highlightthickness=0,state='disabled')
        self.resize_job=None;self.focus_index=-1
        self.canvas.bind('<Configure>',self.resized)
        self.canvas.bind('<Button-1>',self.click_action)
        self.canvas.bind('<Tab>',self.focus_next)
        self.canvas.bind('<Return>',self.invoke_focused)
        self.canvas.bind('<space>',self.invoke_focused)
        self.layout(900,860)
        self.add_log('准备就绪。开启定时后，每天按计划发送。',persist=False)
        root.after(300,self.tick);root.after(100,self.poll)

    def resized(self,event):
        if self.resize_job:self.root.after_cancel(self.resize_job)
        self.resize_job=self.root.after(100,lambda:self.layout(event.width,event.height))

    def layout(self,w,h):
        self.resize_job=None
        if w<100 or h<100:return
        # Keep content and command state while rebuilding only the presentation.
        labels={}
        for name in ('status','countdown','next_label','arm'):
            obj=getattr(self,name,None)
            if obj:
                labels[name]=self.canvas.itemcget(obj.item,'text')
        for switch in getattr(self,'slot_checks',[]):
            if switch.timer:self.canvas.after_cancel(switch.timer)
        c=self.canvas;c.delete('all');self.actions=[]
        left=max(30,(w-940)//2);right=w-left
        self.background=ImageTk.PhotoImage(glass_background(w,h,left,right))
        c.create_image(0,0,image=self.background,anchor='nw')
        CanvasText(c,left,55,'定时唤醒',31,bold=True)
        CanvasText(c,left,91,'让一条消息，准时出发。',14,MUTED)
        CanvasText(c,right,58,'Codex  /  V1.4',12,MUTED,anchor='e')
        CanvasText(c,left+26,154,'每日发送计划',16,bold=True)
        CanvasText(c,right-26,154,'北京时间 · 点击时间调整',12,MUTED,anchor='e')
        self.slot_buttons=[];self.slot_checks=[]
        for i,(slot,var) in enumerate(zip(self.slots,self.slot_vars)):
            y=207+56*i
            CanvasText(c,left+27,y,['凌晨','上午','下午','晚上'][i],13,MUTED)
            self.slot_buttons.append(Action(self,(left+88,y-23,left+211,y+23),
                f'{slot[0]:02}:{slot[1]:02}',lambda index=i:self.change_time(index),31,anchor='w'))
            CanvasText(c,right-110,y,'每天',12,MUTED,anchor='e')
            self.slot_checks.append(Switch(self,right-80,y-15,var,self.edit))
            if i<3:c.create_line(left+26,y+28,right-26,y+28,fill='#d7e1ee')
        self.next_label=CanvasText(c,left+24,451,'',15,bold=True)
        self.countdown=CanvasText(c,left+24,478,'尚未开启定时',12,MUTED)
        CanvasText(c,left+24,542,'发送内容',15,bold=True)
        CanvasText(c,right-24,542,'GPT-6.1 Sol · 所有时段共用',12,MUTED,anchor='e')
        c.create_window(left+22,565,window=self.editor,anchor='nw',width=right-left-44,height=58)
        self.arm=Action(self,(left,666,left+160,714),'开启定时',self.toggle,15,True)
        self.send=Action(self,(left+176,666,left+312,714),'立即试发…',self.send_now)
        self.check_btn=Action(self,(right-136,666,right,714),'检查连接',self.check_connection)
        CanvasText(c,left,737,'保持电脑开机联网 · 最小化继续计时 · 关闭程序停止',12,MUTED)
        self.dot=CanvasText(c,left,765,'●',12,MUTED)
        self.status=CanvasText(c,left+20,765,'已暂停 · 不会自动发送',12,MUTED)
        self.logs_btn=Action(self,(right-90,750,right,781),'查看记录',self.open_logs,12)
        c.create_window(left,790,window=self.history,anchor='nw',width=right-left,height=max(30,h-805))
        for name,text in labels.items():getattr(self,name).configure(text=text)
        self.refresh_next()
        self.controls(not self.busy)
        self.focus_index=-1

    def click_action(self,event):
        for index,action in enumerate(self.actions):
            x,y,x2,y2=action.bounds
            if x<=event.x<=x2 and y<=event.y<=y2:
                self.canvas.focus_set()
                self.focus_index=index
                action.invoke()
                return 'break'

    def focus_next(self,event=None):
        self.focus_index=(self.focus_index+1)%len(self.actions)
        action=self.actions[self.focus_index]
        self.canvas.delete('focus_ring')
        rounded(self.canvas,action.bounds,10,fill='',outline=BLUE,width=2,tags='focus_ring')
        return 'break'

    def invoke_focused(self,event=None):
        if 0<=self.focus_index<len(self.actions):self.actions[self.focus_index].invoke()
        return 'break'


def main():
    try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError,OSError):pass
    mutex=acquire_single_instance()
    if not mutex:
        ctypes.windll.user32.MessageBoxW(None,'请先关闭旧版或已经打开的定时程序。','Codex 定时唤醒',0)
        return
    root=tk.Tk()
    GlassApp(root,preview='--preview' in sys.argv)
    root.mainloop()


if __name__=='__main__':main()
