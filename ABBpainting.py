# -*- coding: utf-8 -*-
# ABBpainting.py — G-code → ABB RobotStudio RAPID 转换工具 (version 1.2)
# 从 ABBpainting.exe (PyInstaller, Python 3.10) 反编译还原
import re
import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

x_value = 0
y_value = 0
z = 0
LeftUp_z = 0
RightUp_z = 0
LeftDown_z = 0
RightDown_z = 0

desktop_path = os.path.expanduser('~\\Desktop')


def save_info(window):
    """四点调零窗口：保存四个角的Z轴值"""
    try:
        global LeftUp_z, RightUp_z, LeftDown_z, RightDown_z
        LeftUp_z = entry1.get()
        RightUp_z = entry2.get()
        LeftDown_z = entry3.get()
        RightDown_z = entry4.get()
        LeftUp_z = float(LeftUp_z)
        RightUp_z = float(RightUp_z)
        LeftDown_z = float(LeftDown_z)
        RightDown_z = float(RightDown_z)
        window.destroy()
    except Exception:
        messagebox.showinfo('警告', '只能输入数字')


def close_window(window):
    """跳过调零：四个角Z值全部置0"""
    global LeftUp_z, RightUp_z, LeftDown_z, RightDown_z
    LeftUp_z = 0
    RightUp_z = 0
    LeftDown_z = 0
    RightDown_z = 0
    window.destroy()


def create_window():
    """四点调零输入窗口"""
    global entry1, entry2, entry3, entry4
    root = tk.Tk()
    root.title('四点调零，不会详细方法请点击跳过')
    root.geometry('400x300')

    labels = ['左上Z轴', '右上Z轴', '左下Z轴', '右下Z轴']
    entries = []

    for i, label_text in enumerate(labels, 1):
        label = ttk.Label(root, text=label_text)
        label.grid(row=i - 1, column=0, padx=10, pady=10)
        entry = ttk.Entry(root)
        entry.grid(row=i - 1, column=1, padx=10, pady=10)
        entries.append(entry)

    entry1, entry2, entry3, entry4 = entries

    save_button = ttk.Button(root, text='保存', command=lambda: save_info(root))
    save_button.grid(row=4, column=0, columnspan=2, pady=20)

    skip_button = ttk.Button(root, text='跳过', command=lambda: close_window(root))
    skip_button.grid(row=4, column=2, columnspan=2, pady=20)

    root.mainloop()


def Zero(x, y):
    """四点调零：根据工件倾斜计算Z轴补偿"""
    z1 = 0
    z2 = RightUp_z - LeftUp_z
    z3 = LeftDown_z - LeftUp_z
    z4 = RightDown_z - LeftUp_z
    xPct = x / 210
    yPct = y / 297
    x1_z = (z2 - z1) * xPct
    x2_z = (z4 - z3) * xPct
    final_z = (x1_z - x2_z) * yPct
    return final_z


# ========== 主流程 ==========
create_window()

root = tk.Tk()
root.withdraw()

file_types = [('Text Files', '*.gcode'), ('Text Files', '*.txt')]
f_path = filedialog.askopenfilename(
    filetypes=file_types,
    title='请选择gcode路径文件  #version 1.2'
)

if not f_path:
    messagebox.showinfo('提示', '未选择文件，程序结束运行')
    exit()

# 写入MOD文件头
with open(desktop_path + '/output.mod', 'w') as a:
    a.write('MODULE MainModule\n'
            'CONST robtarget DW:=[[296.17,-33.73,500.17],'
            '[0.000173257,-0.28718,0.957877,-0.000280338],'
            '[-1,-1,-1,0],'
            '[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];\n'
            'PROC main()\n')

# 逐行解析G-code
with open(f_path, 'r') as f:
    while (temp := f.readline()):
        pattern = 'X(-?[0-9]+\\.[0-9]*|-?[0-9]+) Y([-?[0-9]+\\.[0-9]*|-?[0-9]+)'
        high = 'Z([-?[0-9]+\\.[0-9]*|-?[0-9]+)'
        match = re.search(pattern, temp)
        up_size = re.search(high, temp)

        if match:
            x_value = float('%.2f' % (float(match.group(1)) + 105))
            y_value = float('%.2f' % (float(match.group(2)) + 148))
            if z == '0.00':
                z = '%.2f' % Zero(x_value, y_value)
            with open(desktop_path + '/output.mod', 'a') as a:
                a.write('MoveL Offs(DW,' + str(y_value) + ',' + str(x_value) + ',' + str(z) + '), v50, z0, tool0;\n')

        if up_size:
            z_value = up_size.group(1)
            z = z_value
            with open(desktop_path + '/output.mod', 'a') as a:
                a.write('MoveL Offs(DW,' + str(y_value) + ',' + str(x_value) + ',' + str(z) + '), v50, z0, tool0;\n')

# 写入MOD文件尾
with open(desktop_path + '/output.mod', 'a') as a:
    a.write('ENDPROC\nENDMODULE')

messagebox.showinfo('Ciallo～(∠・ω< )⌒★', '文件转换完成\n输出路径:' + str(desktop_path) + '\\output.mod')
