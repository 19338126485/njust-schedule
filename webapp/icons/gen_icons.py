from PIL import Image, ImageDraw, ImageFont
import os

out_dir = r"C:\Users\19338\Desktop\学习相关\南京理工大学个人课表项目\webapp\icons"
os.makedirs(out_dir, exist_ok=True)

# 生成 192x192 和 512x512 图标
def gen_icon(size, path):
    img = Image.new("RGB", (size, size), "#2d8cf0")
    draw = ImageDraw.Draw(img)
    
    # 画日历网格
    margin = size // 8
    cell_w = (size - 2 * margin) // 4
    cell_h = (size - 2 * margin) // 5
    
    for row in range(5):
        for col in range(4):
            x = margin + col * cell_w
            y = margin + row * cell_h
            # 随机填充一些cell（模拟课表）
            if (row + col) % 3 == 0 and row > 0:
                colors = ["#ff6b6b", "#4ecdc4", "#ffa726", "#ab47bc", "#66bb6a"]
                draw.rectangle([x+2, y+2, x+cell_w-2, y+cell_h-2], fill=colors[(row*4+col) % len(colors)])
            else:
                draw.rectangle([x+2, y+2, x+cell_w-2, y+cell_h-2], fill=(255,255,255))
    
    img.save(path, "PNG")
    print(f"Generated: {path}")

gen_icon(192, os.path.join(out_dir, "icon-192.png"))
gen_icon(512, os.path.join(out_dir, "icon-512.png"))
print("Done")
