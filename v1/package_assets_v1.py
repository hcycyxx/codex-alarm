"""Create new package icon and Windows version metadata; no remote assets."""
from pathlib import Path
from PIL import Image, ImageDraw

out = Path(__file__).parent
image = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8, 8, 248, 248), radius=54, fill='#0071e3')
draw.ellipse((52, 52, 204, 204), outline='white', width=12)
draw.line((128, 82, 128, 130, 161, 151), fill='white', width=12, joint='curve')
with (out / 'clock_v1.ico').open('xb') as file:
    image.save(file, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (128, 128), (256, 256)])
with (out / 'version_v1.txt').open('x', encoding='utf-8') as file:
    file.write("""VSVersionInfo(
 ffi=FixedFileInfo(filevers=(1,0,0,0), prodvers=(1,0,0,0), mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)),
 kids=[StringFileInfo([StringTable('080404b0', [
 StringStruct('CompanyName', 'Jack'),
 StringStruct('FileDescription', 'Codex 定时唤醒'),
 StringStruct('FileVersion', '1.0.0'),
 StringStruct('ProductName', 'Codex 定时唤醒 V1'),
 StringStruct('ProductVersion', '1.0.0'),
 StringStruct('OriginalFilename', 'Codex定时唤醒_v1.exe')
 ])]), VarFileInfo([VarStruct('Translation', [2052,1200])])])
""")
