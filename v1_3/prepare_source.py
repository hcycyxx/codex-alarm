from pathlib import Path

out = Path(__file__).parent
s = (out.parent/'v1_2/codex_alarm_v1_2.py').read_text(encoding='utf-8')
s = s.replace('V1.2', 'V1.3').replace("root.geometry('860x860')", "root.geometry('860x830')").replace("root.minsize(760, 820)", "root.minsize(760, 800)")
s = s.replace("saved = {} if preview else self.store.load()", """saved = {} if preview else self.store.load()
        previous = saved
        self.store = Store(data_dir.parent / 'v1_3')
        saved = ({} if preview else self.store.load()) or previous
        self.slots = saved.get('slots', [[4,50,True],[9,51,True],[14,52,True],[19,53,True]])
        self.slot_buttons = []
        self.slot_vars = []
        self.slot_checks = []""")
start=s.index("        self.text(top, '发送时间'")
end=s.index("        self.next_label =",start)
s=s[:start]+'''        self.text(top, '每日发送计划', 13, bold=True, bg='white').pack(side='left')
        self.text(top, '北京时间 · 点击时间可调整', 9, MUTED, bg='white').pack(side='right')
        self.repeat = tk.BooleanVar(value=True)
        self.check = tk.Checkbutton(top, variable=self.repeat)
        # Hidden compatibility controls retain the proven sending code.
        hidden = tk.Frame(schedule)
        self.hour = Wheel(hidden, 24, 4, self.edit, '小时')
        self.minute = Wheel(hidden, 60, 50, self.edit, '分钟')
        names = ['凌晨', '上午', '下午', '晚上']
        for i, slot in enumerate(self.slots):
            if i:
                tk.Frame(schedule, bg='#ededf0', height=1).pack(fill='x')
            row = tk.Frame(schedule, bg='white')
            row.pack(fill='x', pady=8)
            self.text(row, names[i], 10, MUTED, bg='white').pack(side='left', padx=(0, 23))
            button = tk.Button(row, text=f'{slot[0]:02}:{slot[1]:02}', font=('Segoe UI', 25),
                bg='white', fg=INK, bd=0, relief='flat', cursor='hand2',
                activebackground='#f1f1f4', command=lambda index=i: self.change_time(index))
            button.pack(side='left')
            self.slot_buttons.append(button)
            var = tk.BooleanVar(value=slot[2])
            self.slot_vars.append(var)
            check = tk.Checkbutton(row, text='每天', variable=var, bg='white', fg=MUTED,
                activebackground='white', selectcolor='white', command=self.edit)
            check.pack(side='right')
            self.slot_checks.append(check)

'''+s[end:]
s=s.replace("        return {'hour':", "        return {'slots': [[slot[0],slot[1],var.get()] for slot,var in zip(self.slots,self.slot_vars)], 'hour':")
s=s.replace("now = dt.datetime.now()", "now = self.beijing_now()")
s=s.replace("next_occurrence(self.hour.value, self.minute.value, now)", "self.next_due(now)")
s=s.replace("next_occurrence(self.hour.value, self.minute.value)", "self.next_due(self.beijing_now())")
s=s.replace("        day = '今天'", "        if upcoming is None:\n            self.next_label.configure(text='所有时段已关闭')\n            return\n        day = '今天'")
s=s.replace("('每天' if self.repeat.get() else '仅一次')", "'北京时间'")
s=s.replace("        self.active = True\n", "        if self.due is None:\n            messagebox.showinfo('请选择时段', '请至少开启一个发送时段。', parent=self.root)\n            return\n        self.active = True\n")
s=s.replace("('每天重复。' if self.repeat.get() else '仅发送一次。')", "'每天按已开启的时段发送。'")
s=s.replace("        for button in (self.send, self.check_btn, self.arm, self.check):", "        for button in (self.send, self.check_btn, self.arm, self.check, *self.slot_buttons, *self.slot_checks):")
insert=s.index('    def text(self, parent,')
s=s[:insert]+'''    @staticmethod
    def beijing_now():
        return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).replace(tzinfo=None)

    def next_due(self, now):
        choices = [next_occurrence(slot[0], slot[1], now)
                   for slot, var in zip(self.slots, self.slot_vars) if var.get()]
        return min(choices) if choices else None

    def change_time(self, index):
        if self.busy:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title('调整发送时间')
        dialog.configure(bg='white')
        dialog.geometry('340x340')
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        tk.Label(dialog, text='每天 · 北京时间', bg='white', fg=MUTED,
                 font=(FONT, 11)).pack(pady=(18, 5))
        row = tk.Frame(dialog, bg='white')
        row.pack()
        hour = Wheel(row, 24, self.slots[index][0], lambda: None, '小时')
        minute = Wheel(row, 60, self.slots[index][1], lambda: None, '分钟')
        hour.pack(side='left')
        minute.pack(side='left')
        def apply():
            self.slots[index][:2] = [hour.value, minute.value]
            self.slot_buttons[index].configure(text=f'{hour.value:02}:{minute.value:02}')
            self.edit()
            dialog.destroy()
        tk.Button(dialog, text='保存时间', command=apply, bg=BLUE, fg='white',
                  relief='flat', padx=30, pady=9).pack(pady=10)

'''+s[insert:]
with (out/'codex_alarm_v1_3.py').open('x',encoding='utf-8') as f:f.write(s)
v=(out.parent/'v1_2/version_v1_2.txt').read_text(encoding='utf-8').replace('1,2,0,0','1,3,0,0').replace('1.2.0','1.3.0').replace('V1.2','V1.3').replace('_v1_2','_v1_3')
with (out/'version_v1_3.txt').open('x',encoding='utf-8') as f:f.write(v)
b=(out.parent/'v1_2/build_v1_2.ps1').read_text(encoding='utf-8').replace('_v1_2','_v1_3')
with (out/'build_v1_3.ps1').open('x',encoding='utf-8-sig') as f:f.write(b)
