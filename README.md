# ABBpainting

让 ABB 机器人照着图把线画出来。G-code 进去，RobotStudio 的 RAPID 模块出来。

## 为什么要写这个

想用机器人画二次元线稿，路子基本是固定的：

```
图片 → Inkscape 描摹成矢量 → 导出 G-code → ? → RAPID
```

前后都有现成软件，中间断了一截。G-code 是纯平面坐标，可纸贴在板子上不可能绝对平，笔尖要么戳穿要么悬空，画到后面整张图就歪了。

这个工具补的就是这截：先在板子四角各量一个 Z，再按位置算每个点该抬多少。

`assets/` 里是当时用的素材，同一个角色的线稿和上色版。描摹一定要用线稿，彩图描出来是一坨色块。

## 下载

Windows 直接跑，不用装 Python：

<https://github.com/fegrous/ABBpainting/releases/download/v1.2.0/ABBpainting.exe>

仓库里只放源码，二进制走 release，省得占两遍体积。

## 怎么用

先出 G-code。Inkscape 打开线稿，`路径 > 描摹位图`，再用 G-code 导出插件（Gcodetools、J Tech Laser 之类）导出 `.gcode`。

落笔那一行的 Z 必须是 `Z0.00`。程序靠这个字符串判断该不该做补偿，写成 `Z0.0`、`Z.00` 它都不认。

然后双击 exe。先弹一个四点调零窗口，四个框分别是左上、右上、左下、右下四角的 Z 值，单位 mm。不想补偿就点跳过，四角按 0 算。填了非数字会提示"只能输入数字"，窗口不关。

接着选刚才那个 gcode。转完弹窗提示，文件固定落在桌面：

```
%USERPROFILE%\Desktop\output.mod
```

把这个 `output.mod` 拖进 RobotStudio 的 RAPID 模块里，齐活。

## 输出的样子

```rapid
MODULE MainModule
CONST robtarget DW:=[[296.17,-33.73,500.17],[0.000173257,-0.28718,0.957877,-0.000280338],[-1,-1,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
PROC main()
MoveL Offs(DW,266.00,180.00,0), v50, z0, tool0;
MoveL Offs(DW,266.00,180.00,0.00), v50, z0, tool0;
MoveL Offs(DW,266.00,240.00,0.12), v50, z0, tool0;
MoveL Offs(DW,326.00,240.00,0.24), v50, z0, tool0;
MoveL Offs(DW,326.00,180.00,0.12), v50, z0, tool0;
ENDPROC
ENDMODULE
```

`DW` 是写死的基准点，换工件或者换机器人得改源码重新打包。

还有个地方容易看错：`Offs(DW, a, b, c)` 里 `a` 是 G-code 的 Y，`b` 才是 X。XY 是反着输出的，相当于把图纸转了 90 度。速度 `v50`、转弯区 `z0`、工具 `tool0` 同样都写死了。

## 四点调零到底算了什么

先把图纸挪到原点附近：

```
x_value = G-code 的 X + 105      # 105 = A4 宽 210 的一半
y_value = G-code 的 Y + 148      # 148 ≈ A4 高 297 的一半
```

这样一张 A4 幅面画出来正好以 `DW` 为中心。然后拿四角的 Z 值算补偿：

```
xPct = x_value / 210
yPct = y_value / 297

x1_z = (右上 - 左上) * xPct
x2_z = (右下 - 左下) * xPct
Z    = (x1_z - x2_z) * yPct
```

展开就是 `Z = [(右上-左上) - (右下-左下)] × xPct × yPct`。

这里有个很容易被忽略的性质：**板子只要是平的，不管它斜不斜，四角必然满足 `(右上-左上) = (右下-左下)`，代进去 Z 恒等于 0。**

也就是说这个算法根本不补偿倾斜，只补偿对角线方向上的翘曲。倾斜要交给机器人的工作坐标系（wobj）去摆正，四点调零管的是摆正之后残留的那点不平。如果工件真是个斜面又没建 wobj，它帮不上忙。

另外，虽然函数注释写的是"双线性插值"，严格讲不是。完整的双线性插值还带一个常数项和两个线性项，这里只取了扭曲那一项。扭曲量本来就小，实机上差别感觉不出来，但既然要写文档就写准一点。

## 已知的毛病

- 一行里同时有 XY 和 Z 的话，会输出两条 MoveL。代码是先判断 XY、再判断 Z，两次都写了。如果 gcode 每行都带 Z，前一条的插值结果会被后一条覆盖掉，还留下一堆多余指令。可能本来就这么设计的，也可能是 bug，用之前自己看一眼输出。
- 补偿值会粘住。只有当前 z 恰好等于字符串 `"0.00"` 时才重新算，中间没出现 `Z0.00` 的一长串指令会一直复用第一次那个值。
- 输出路径写死在桌面上（`%USERPROFILE%\Desktop\output.mod`），桌面被重定向到 OneDrive、或者不在 Windows 上跑，直接就失败。
- 没有批量，一次一个文件。

## 改源码 / 重新打包

`ABBpainting.py` 是从 exe 反编译还原的，行为跟原版一致。想换基准点、改输出路径、加批量，都从这儿改。

```bash
python ABBpainting.py
```

打包成单文件 exe：

```bash
pip install pyinstaller
pyinstaller -F -w --name ABBpainting ABBpainting.py
```

需要 Python 3.10+，只用了标准库 `re` / `os` / `tkinter`。

## 还有个 Inkscape

原来那套流程里带了个便携版 Inkscape，负责描摹和导出 G-code。200 多 MB，没往仓库里放，要的话自己去 [inkscape.org](https://inkscape.org/release/) 下，或者换别的能描摹位图加导 gcode 的软件。

## 目录

```
ABBpainting.py       v1.2 源码（反编译还原）
assets/murasame.png  线稿
assets/cy.png        上色稿
LICENSE  README.md  .gitignore
```

MIT
