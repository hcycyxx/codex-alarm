from pathlib import Path
p=Path(__file__).parent
s=(p.parent/'v1_4/codex_alarm_v1_4.py').read_text(encoding='utf-8')
s=s.replace("MUTED = '#52617a'", "MUTED = '#3e5069'")
s=s.replace("font=(FONT,-size,'bold' if bold else 'normal')", "font=('Segoe UI' if text.replace(':','').isdigit() else FONT,-round(size*1.25),'bold' if bold else 'normal')")
s=s.replace("font=(FONT,-15)","font=(FONT,-19)").replace("font=(FONT,-12)","font=(FONT,-15)")
s=s.replace("('v1_4','v1_3','v1')", "('v1_5','v1_4','v1_3','v1')").replace("Store(parent/'v1_4')", "Store(parent/'v1_5')")
s=s.replace('V1.4','V1.5')
s=s.replace("fill=(115,186,255,190)","fill=(115,186,255,120)").replace("fill=(207,171,249,165)","fill=(207,171,249,100)")
s=s.replace("mask=Image.new('L',(x2-x,y2-y));md=ImageDraw.Draw(mask)\n        md.rounded_rectangle((0,0,x2-x-1,y2-y-1),radius,fill=255)","mask=Image.new('L',((x2-x)*4,(y2-y)*4));md=ImageDraw.Draw(mask)\n        md.rounded_rectangle((0,0,(x2-x)*4-1,(y2-y)*4-1),radius*4,fill=255)\n        mask=mask.resize((x2-x,y2-y),Image.Resampling.LANCZOS)")
a=s.index('        edge=ImageDraw.Draw(base)');b=s.index('    return base',a)
s=s[:a]+'''        edge=Image.new('RGBA',((x2-x)*4,(y2-y)*4))
        ed=ImageDraw.Draw(edge)
        ed.rounded_rectangle((2,2,edge.width-3,edge.height-3),radius*4,
                             outline=(255,255,255,190),width=4)
        edge=edge.resize((x2-x,y2-y),Image.Resampling.LANCZOS)
        base.alpha_composite(edge,(x,y))
'''+s[b:]
s=s.replace("        c=self.canvas;c.delete('all');self.actions=[]", "        pixel_w,pixel_h=w,h\n        scale=max(1.,min(w/900,h/860,1.5))\n        self.ui_scale=scale\n        w,h=round(w/scale),round(h/scale)\n        c=self.canvas;c.delete('all');self.actions=[]")
s=s.replace("ImageTk.PhotoImage(glass_background(w,h,left,right))", "ImageTk.PhotoImage(glass_background(w,h,left,right).resize((pixel_w,pixel_h),Image.Resampling.LANCZOS))")
s=s.replace("c.create_image(0,0,image=self.background,anchor='nw')", "c.create_image(0,0,image=self.background,anchor='nw',tags='background')")
s=s.replace("height=max(30,h-805)","height=min(76,max(30,h-805))")
needle="        self.focus_index=-1\n\n    def click_action"
s=s.replace(needle,'''        self.focus_index=-1
        for item in c.find_all():
            if 'background' in c.gettags(item):continue
            c.scale(item,0,0,scale,scale)
            if c.type(item)=='text':
                import tkinter.font as tkfont
                font=tkfont.Font(font=c.itemcget(item,'font'))
                c.itemconfigure(item,font=(font.actual('family'),-round(abs(font.cget('size'))*scale),font.actual('weight')))
            elif c.type(item)=='window':
                c.itemconfigure(item,width=round(float(c.itemcget(item,'width'))*scale),
                                height=round(float(c.itemcget(item,'height'))*scale))
        for action in self.actions:
            action.bounds=tuple(n*scale for n in action.bounds)
            if isinstance(action,Switch):
                action.x*=scale;action.y*=scale;action.scale=scale;action.draw()
        self.editor.configure(font=(FONT,-round(19*scale)))
        self.history.configure(font=(FONT,-round(15*scale)))

    def click_action''')
s=s.replace("        c=self.canvas;x=self.x;y=self.y", "        c=self.canvas;x=self.x;y=self.y\n        z=getattr(self,'scale',1.)")
s=s.replace("c.create_line(x+15,y+15,x+39,y+15,fill=track,width=30", "c.create_line(x+15*z,y+15*z,x+39*z,y+15*z,fill=track,width=30*z")
s=s.replace("cx=x+15+24*self.position", "cx=x+(15+24*self.position)*z")
s=s.replace("cx-12,y+4,cx+12,y+28", "cx-12*z,y+4*z,cx+12*z,y+28*z").replace("cx-12,y+3,cx+12,y+27", "cx-12*z,y+3*z,cx+12*z,y+27*z")
with (p/'codex_alarm_v1_5.py').open('x',encoding='utf-8') as f:f.write(s)
for source,dest in [('version_v1_4.txt','version_v1_5.txt'),('build_v1_4.ps1','build_v1_5.ps1')]:
    s=(p.parent/'v1_4'/source).read_text(encoding='utf-8-sig').replace('1,4,0,0','1,5,0,0').replace('1.4.0','1.5.0').replace('V1.4','V1.5').replace('_v1_4','_v1_5')
    with (p/dest).open('x',encoding='utf-8-sig' if dest.endswith('.ps1') else 'utf-8') as f:f.write(s)
