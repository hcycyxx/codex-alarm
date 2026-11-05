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
from window_chrome import WindowChrome

INK = '#17243b'
MUTED = '#3e5069'
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
            font=('Segoe UI' if text.replace(':','').isdigit() else FONT,-round(size*1.25),'bold' if bold else 'normal'))

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
        z=getattr(self,'scale',1.)
        c.delete(self.tag)
        track='#31bd70' if self.var.get() and self.enabled else '#bac6d5'
        c.create_line(x+15*z,y+15*z,x+39*z,y+15*z,fill=track,width=30*z,capstyle='round',tags=self.tag)
        cx=x+(15+24*self.position)*z
        c.create_oval(cx-12*z,y+4*z,cx+12*z,y+28*z,fill='#699c86' if self.var.get() else '#9ca9b9',outline='',tags=self.tag)
        c.create_oval(cx-12*z,y+3*z,cx+12*z,y+27*z,fill='white',outline='#edf2f6',tags=self.tag)
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


class WindowAction(Action):
    def __init__(self, app, bounds, kind, command):
        super().__init__(app, bounds, '', command)
        x,y,x2,y2 = bounds
        cx,cy = (x+x2)/2,(y+y2)/2
        c = app.canvas
        # Draw consistent vector icons rather than font-dependent symbols.
        if kind == 'min':
            c.create_line(cx-6,cy,cx+6,cy,fill=INK,width=1.5)
        elif kind == 'max':
            c.create_rectangle(cx-5,cy-5,cx+5,cy+5,outline=INK,width=1.4)
        else:
            c.create_line(cx-5,cy-5,cx+5,cy+5,fill=INK,width=1.5)
            c.create_line(cx+5,cy-5,cx-5,cy+5,fill=INK,width=1.5)


def glass_background(width,height,left,right):
    # Refraction and blur of this application's own background, not the desktop.
    w,h=max(1,width//3),max(1,height//3)
    base=Image.new('RGB',(w,h),'#e5edf7')
    layer=Image.new('RGBA',(w,h));d=ImageDraw.Draw(layer)
    d.ellipse((-w*.4,-h*.25,w*.65,h*.55),fill=(115,186,255,120))
    d.ellipse((w*.4,-h*.2,w*1.5,h*.7),fill=(207,171,249,100))
    d.ellipse((-w*.25,h*.65,w*.8,h*1.5),fill=(129,212,223,135))
    d.ellipse((w*.7,h*.5,w*1.4,h*1.2),fill=(255,212,184,135))
    base=Image.alpha_composite(base.convert('RGBA'),layer.filter(ImageFilter.GaussianBlur(65)))
    base=base.resize((width,height),Image.Resampling.BICUBIC)
    for bounds,radius in [((left,126,right,448),28),((left,466,right,535),23),
                          ((left,554,right,684),25),((left,704,left+160,752),24),
                          ((left+176,704,left+312,752),24),((right-136,704,right,752),24),
                          ((right-212,137,right-116,173),18),((right-106,137,right-20,173),18)]:
        x,y,x2,y2=map(int,bounds)
        shadow=Image.new('RGBA',base.size);sd=ImageDraw.Draw(shadow)
        sd.rounded_rectangle((x+1,y+8,x2+1,y2+10),radius,fill=(67,87,126,25))
        base=Image.alpha_composite(base,shadow.filter(ImageFilter.GaussianBlur(12)))
        mask=Image.new('L',((x2-x)*4,(y2-y)*4));md=ImageDraw.Draw(mask)
        md.rounded_rectangle((0,0,(x2-x)*4-1,(y2-y)*4-1),radius*4,fill=255)
        mask=mask.resize((x2-x,y2-y),Image.Resampling.LANCZOS)
        refracted=base.crop((x,y,x2,y2)).filter(ImageFilter.GaussianBlur(10))
        refracted=Image.blend(refracted,Image.new('RGBA',refracted.size,'white'),.56)
        if y==704 and x==left:
            refracted=Image.blend(refracted,Image.new('RGBA',refracted.size,'#0075ed'),.93)
        base.paste(refracted,(x,y),mask)
        edge=Image.new('RGBA',((x2-x)*4,(y2-y)*4))
        ed=ImageDraw.Draw(edge)
        ed.rounded_rectangle((2,2,edge.width-3,edge.height-3),radius*4,
                             outline=(255,255,255,190),width=4)
        edge=edge.resize((x2-x,y2-y),Image.Resampling.LANCZOS)
        base.alpha_composite(edge,(x,y))
    return base


class GlassApp(BaseApp):
    def __init__(self,root,preview=False):
        self.root,self.preview=root,preview
        parent=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'CodexAlarm'
        saved={}
        if not preview:
            for version in ('v1_6','v1_5','v1_4','v1_3','v1'):
                folder=parent/version
                if folder.exists():
                    saved=Store(folder).load()
                    if saved:break
        self.store=Store(parent/'v1_6')
        self.slots=saved.get('slots',[[4,50,True],[9,51,True],[14,52,True],[19,53,True]])
        self.thread_id=saved.get('thread_id','')
        self.last_attempt=saved.get('last_attempt','')
        self.active,self.busy,self.due=False,False,None
        self.busy_kind=None;self.results=queue.Queue();self.rpc=None
        self.slot_vars=[tk.BooleanVar(value=s[2]) for s in self.slots]
        self.plan_page=0
        self.repeat=tk.BooleanVar(value=True)
        self.check=tk.Checkbutton(root,variable=self.repeat)
        self.hour=Wheel(root,24,4,self.edit,'小时')
        self.minute=Wheel(root,60,50,self.edit,'分钟')
        root.title('Codex 定时唤醒 · V1.6')
        root.geometry('900x920');root.minsize(790,900)
        root.configure(bg='#e5edf7')
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.canvas=tk.Canvas(root,bd=0,highlightthickness=0,bg='#e5edf7',takefocus=True)
        self.canvas.pack(fill='both',expand=True)
        self.editor=tk.Text(root,wrap='word',height=2,bg='#f1f5fc',fg=INK,
            font=(FONT,-19),bd=0,highlightthickness=0,insertbackground=BLUE,
            selectbackground='#b9d9ff',undo=True,padx=6,pady=5)
        self.editor.insert('1.0',saved.get('message','只回复 OK。'))
        self.editor.edit_modified(False)
        self.editor.bind('<<Modified>>',self.message_changed)
        self.history=tk.Text(root,bg='#e3edf8',fg=MUTED,wrap='word',height=2,
            font=(FONT,-15),bd=0,highlightthickness=0,state='disabled')
        self.resize_job=None;self.focus_index=-1
        self.canvas.bind('<Configure>',self.resized)
        self.canvas.bind('<Button-1>',self.click_action)
        self.canvas.bind('<Tab>',self.focus_next)
        self.canvas.bind('<Return>',self.invoke_focused)
        self.canvas.bind('<space>',self.invoke_focused)
        self.layout(900,920)
        root.update_idletasks()
        self.chrome=WindowChrome(root)
        root.after(100,lambda:self.layout(root.winfo_width(),root.winfo_height()))
        self.add_log('准备就绪。开启定时后，每天按计划发送。',persist=False)
        root.after(300,self.tick);root.after(100,self.poll)

    def resized(self,event):
        if self.resize_job:self.root.after_cancel(self.resize_job)
        self.resize_job=self.root.after(100,lambda:self.layout(event.width,event.height))

    def layout(self,w,h):
        self.resize_job=None
        if w<100 or h<100:return
        if hasattr(self,'chrome'):self.chrome.update_region()
        # Keep content and command state while rebuilding only the presentation.
        labels={}
        for name in ('status','countdown','next_label','arm'):
            obj=getattr(self,name,None)
            if obj:
                labels[name]=self.canvas.itemcget(obj.item,'text')
        for switch in getattr(self,'slot_checks',[]):
            if switch.timer:self.canvas.after_cancel(switch.timer)
        pixel_w,pixel_h=w,h
        scale=max(1.,min(w/900,h/920,1.5))
        self.ui_scale=scale
        w,h=round(w/scale),round(h/scale)
        c=self.canvas;c.delete('all');self.actions=[]
        left=max(30,(w-940)//2);right=w-left
        self.background=ImageTk.PhotoImage(glass_background(w,h,left,right).resize((pixel_w,pixel_h),Image.Resampling.LANCZOS))
        c.create_image(0,0,image=self.background,anchor='nw',tags='background')
        # The title strip shares the same glass background as the application.
        WindowAction(self,(w-158,4,w-110,36),'min',lambda:self.chrome.minimize())
        WindowAction(self,(w-108,4,w-60,36),'max',lambda:self.chrome.maximize())
        WindowAction(self,(w-58,4,w-10,36),'close',self.close)
        CanvasText(c,left,55,'定时唤醒',31,bold=True)
        CanvasText(c,left,91,'让一条消息，准时出发。',14,MUTED)
        CanvasText(c,right,65,'Codex  /  V1.6',12,MUTED,anchor='e')
        CanvasText(c,left+26,154,'每日发送计划',16,bold=True)
        self.plan_add=Action(self,(right-212,137,right-116,173),'新增',self.add_plan,13)
        self.plan_remove=Action(self,(right-106,137,right-20,173),'删除',self.delete_plan,13)
        self.slot_buttons=[];self.slot_checks=[]
        self.plan_page=min(self.plan_page,max(0,(len(self.slots)-1)//4))
        first=self.plan_page*4
        for row,i in enumerate(range(first,min(first+4,len(self.slots)))):
            slot,var=self.slots[i],self.slot_vars[i]
            y=207+56*row
            period='凌晨' if slot[0]<6 else '上午' if slot[0]<12 else '下午' if slot[0]<18 else '晚上'
            CanvasText(c,left+27,y,period,13,MUTED)
            self.slot_buttons.append(Action(self,(left+88,y-23,left+211,y+23),
                f'{slot[0]:02}:{slot[1]:02}',lambda index=i:self.change_time(index),31,anchor='w'))
            CanvasText(c,right-110,y,'每天',12,MUTED,anchor='e')
            self.slot_checks.append(Switch(self,right-80,y-15,var,self.edit))
            if row<3:c.create_line(left+26,y+28,right-26,y+28,fill='#d7e1ee')
        if not self.slots:
            CanvasText(c,(left+right)/2,272,'还没有发送计划',20,MUTED,anchor='center')
            CanvasText(c,(left+right)/2,312,'点击右上角“新增”，设置每天发送的时间',13,MUTED,anchor='center')
        CanvasText(c,left+26,426,f'共 {len(self.slots)} 项 · 北京时间 · 点击时间调整',12,MUTED)
        self.page_prev=self.page_next=None
        if len(self.slots)>4:
            self.page_prev=Action(self,(right-232,408,right-156,443),'上一页',lambda:self.turn_page(-1),12)
            CanvasText(c,right-118,426,f'{self.plan_page+1}/{(len(self.slots)+3)//4}',12,MUTED,anchor='center')
            self.page_next=Action(self,(right-80,408,right-4,443),'下一页',lambda:self.turn_page(1),12)
        self.next_label=CanvasText(c,left+24,489,'',15,bold=True)
        self.countdown=CanvasText(c,left+24,516,'尚未开启定时',12,MUTED)
        CanvasText(c,left+24,580,'发送内容',15,bold=True)
        CanvasText(c,right-24,580,'GPT-6.1 Sol · 所有时段共用',12,MUTED,anchor='e')
        c.create_window(left+22,603,window=self.editor,anchor='nw',width=right-left-44,height=58)
        self.arm=Action(self,(left,704,left+160,752),'开启定时',self.toggle,15,True)
        self.send=Action(self,(left+176,704,left+312,752),'立即试发…',self.send_now)
        self.check_btn=Action(self,(right-136,704,right,752),'检查连接',self.check_connection)
        CanvasText(c,left,775,'保持电脑开机联网 · 最小化继续计时 · 关闭程序停止',12,MUTED)
        self.dot=CanvasText(c,left,803,'●',12,MUTED)
        self.status=CanvasText(c,left+20,803,'已暂停 · 不会自动发送',12,MUTED)
        self.logs_btn=Action(self,(right-90,788,right,819),'查看记录',self.open_logs,12)
        c.create_window(left,828,window=self.history,anchor='nw',width=right-left,height=min(76,max(30,h-843)))
        for name,text in labels.items():getattr(self,name).configure(text=text)
        self.refresh_next()
        self.controls(not self.busy)
        self.focus_index=-1
        for item in c.find_all():
            if 'background' in c.gettags(item):continue
            c.scale(item,0,0,scale,scale)
            if c.type(item)=='text':
                parts=c.tk.splitlist(c.itemcget(item,'font'))
                c.itemconfigure(item,font=(parts[0],round(int(parts[1])*scale),parts[2]))
            elif c.type(item)=='window':
                widget=c.itemcget(item,'window')
                if widget==str(self.editor):
                    c.itemconfigure(item,width=round((right-left-44)*scale),height=round(58*scale))
                else:
                    c.itemconfigure(item,width=round((right-left)*scale),height=round(min(76,max(30,h-843))*scale))
        for action in self.actions:
            action.bounds=tuple(n*scale for n in action.bounds)
            if isinstance(action,Switch):
                action.x*=scale;action.y*=scale;action.scale=scale;action.draw()
        self.editor.configure(font=(FONT,-round(19*scale)))
        self.history.configure(font=(FONT,-round(15*scale)))

    def controls(self,enabled):
        super().controls(enabled)
        for button in (getattr(self,'plan_add',None),getattr(self,'plan_remove',None),
                       getattr(self,'page_prev',None),getattr(self,'page_next',None)):
            if button:button.configure(state='normal' if enabled else 'disabled')
        if not self.slots:self.plan_remove.configure(state='disabled')
        if self.page_prev and self.plan_page==0:self.page_prev.configure(state='disabled')
        if self.page_next and self.plan_page>=(len(self.slots)-1)//4:self.page_next.configure(state='disabled')

    def turn_page(self,step):
        if self.busy:return
        self.plan_page=max(0,min(self.plan_page+step,max(0,(len(self.slots)-1)//4)))
        self.layout(self.root.winfo_width(),self.root.winfo_height())

    def add_plan(self):
        self.time_dialog(None)

    def change_time(self,index):
        self.time_dialog(index)

    def time_dialog(self,index):
        if self.busy:return
        dialog=tk.Toplevel(self.root)
        dialog.title('新增每日计划' if index is None else '调整发送时间')
        dialog.configure(bg='#edf3fb')
        dialog.geometry('390x370');dialog.resizable(False,False)
        dialog.transient(self.root);dialog.grab_set()
        if index is None:
            now=self.beijing_now()
            total=(now.hour*60+now.minute+5)%1440
            used={(slot[0],slot[1]) for slot in self.slots}
            for _ in range(1440):
                if (total//60,total%60) not in used:break
                total=(total+1)%1440
            h,m=divmod(total,60)
        else:h,m=self.slots[index][:2]
        tk.Label(dialog,text='每天 · 北京时间',font=(FONT,-19),fg=INK,bg='#edf3fb').pack(pady=(23,8))
        row=tk.Frame(dialog,bg='white');row.pack()
        hour=Wheel(row,24,h,lambda:None,'小时');hour.pack(side='left',padx=7)
        minute=Wheel(row,60,m,lambda:None,'分钟');minute.pack(side='left',padx=7)
        def apply():
            try:self.apply_plan(hour.value,minute.value,index)
            except ValueError as error:
                messagebox.showinfo('请调整时间',str(error),parent=dialog);return
            except OSError as error:
                messagebox.showerror('保存失败',str(error),parent=dialog);return
            dialog.destroy()
        tk.Button(dialog,text='添加计划' if index is None else '保存时间',command=apply,
                  bg=BLUE,fg='white',font=(FONT,-18),relief='flat',padx=35,pady=10).pack(pady=19)

    def apply_plan(self,hour,minute,index=None):
        if self.busy:return
        if any(i!=index and slot[:2]==[hour,minute] for i,slot in enumerate(self.slots)):
            raise ValueError('这个时间已经有计划了，请选择其他时间。')
        if index is None:
            self.slots.append([hour,minute,True])
            self.slot_vars.append(tk.BooleanVar(value=True))
        else:self.slots[index][:2]=[hour,minute]
        target=next(slot for slot in self.slots if slot[:2]==[hour,minute])
        paired=sorted(zip(self.slots,self.slot_vars),key=lambda pair:pair[0][:2])
        self.slots=[pair[0] for pair in paired];self.slot_vars=[pair[1] for pair in paired]
        self.plan_page=next(i for i,slot in enumerate(self.slots) if slot is target)//4
        self.edit()
        self.save()
        self.layout(self.root.winfo_width(),self.root.winfo_height())

    def delete_plan(self):
        if self.busy or not self.slots:return
        dialog=tk.Toplevel(self.root)
        dialog.title('删除每日计划');dialog.geometry('390x370')
        dialog.configure(bg='#edf3fb');dialog.transient(self.root);dialog.grab_set()
        tk.Label(dialog,text='选择要删除的计划',font=(FONT,-19),bg='#edf3fb',fg=INK).pack(pady=18)
        choices=tk.Listbox(dialog,selectmode='extended',font=('Segoe UI',-23),bd=0,
                           selectbackground='#cbe3ff',selectforeground=INK,exportselection=False)
        choices.pack(fill='both',expand=True,padx=24)
        for slot,var in zip(self.slots,self.slot_vars):
            choices.insert('end',f"  {slot[0]:02}:{slot[1]:02}    {'每天' if var.get() else '已关闭'}")
        def remove():
            indices=list(choices.curselection())
            if not indices:return
            if not messagebox.askokcancel('删除计划',f'删除选中的 {len(indices)} 个每日时段？',parent=dialog):return
            try:self.remove_plans(indices)
            except OSError as error:
                messagebox.showerror('保存失败',str(error),parent=dialog);return
            dialog.destroy()
        tk.Button(dialog,text='删除所选',command=remove,bg='#c44242',fg='white',relief='flat',
                  font=(FONT,-18),padx=30,pady=10).pack(pady=18)

    def remove_plans(self,indices):
        if self.busy:return
        for index in sorted(set(indices),reverse=True):
            del self.slots[index];del self.slot_vars[index]
        self.edit()
        self.save()
        self.layout(self.root.winfo_width(),self.root.winfo_height())

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
