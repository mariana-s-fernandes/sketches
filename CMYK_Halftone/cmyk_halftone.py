import numpy as np
import vpype as vp

import vsketch
from PIL import Image
from scipy import ndimage
import glob

from vpype.utils import PAGE_SIZES

CMYK_ANGLES = [15, 75, 0, 45]
CMYK_COLORS = [(0,255,255), (255,0,255), (255,255,0)]
ext = ['jpg', 'png']
images = []
[images.extend(glob.glob('*.' + e)) for e in ext]
IMG_PATH = 'mountains.jpg'

def cmyk_radius(value, maxRadius):
    r = (255-value) /255 * maxRadius
    return  r

def map_range(value, start1, stop1, start2, stop2):
   return (value - start1) / (stop1 - start1) * (stop2 - start2) + start2


class CMYK_Halftone(vsketch.SketchClass):
    # Sketch parameters:
    page_size = vsketch.Param("a4", choices=PAGE_SIZES)
    image = vsketch.Param(IMG_PATH, choices=images)
    orient = vsketch.Param("landscape", choices=["portrait", "landscape"])
    center = vsketch.Param(True)
    pitch = vsketch.Param(0.5, 0.0, unit="cm", step=0.125, decimals=3)
    num_x = vsketch.Param(100, 1)
    scale = vsketch.Param(0.8)
    use_k_channel = vsketch.Param(False) # not working with PIL
    pen_width = vsketch.Param(0.3, unit="mm", step=0.05)
    max_radius = vsketch.Param(0.7)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size("a4", landscape=(self.orient == "landscape"), center=self.center)
        vsk.penWidth(self.pen_width)

        if self.orient == "landscape":
            page_h, page_w = vp.convert_page_size("a4")
        else:
            page_w, page_h = vp.convert_page_size("a4")

        img = Image.open(IMG_PATH).convert("RGBA")
        x_pixels, y_pixels = img.size

        num_y = int(np.floor(self.num_x*y_pixels/x_pixels))
        img_transf = img.resize((self.num_x, num_y))
        img_array = np.array(img_transf)

        max_size = int(np.ceil(np.sqrt(self.num_x**2 + num_y**2)))

        final_x = np.ceil(self.scale*page_w*max_size/self.num_x)
        max_radius = int(round(self.max_radius*final_x/(2*max_size)))

        print('Page size:', page_w, page_h)
        print('Final image size:', final_x)
        print('Pixels:', self.num_x, num_y)
        print('Max circle radius:', max_radius)

        if self.use_k_channel:
            CMYK_COLORS.append((0,0,0))
        
        print(CMYK_COLORS)
        print(len(CMYK_ANGLES))
        
        for i, _ in enumerate(CMYK_COLORS):
            angle = CMYK_ANGLES[i]
            
            img_r = ndimage.rotate(img_array, angle)

            img_transf = Image.fromarray(img_r)

            img_w, img_h = img_transf.size
            print(f'Rotated image size {i}:', img_w, img_h)

            offset = (round((max_size - img_w) / 2), round((max_size - img_h) / 2))
            print('Offset:', offset)

            img_bg = Image.new("RGBA", (max_size, max_size), color=(255,255,255)) # Create a white rgba background
            img_bg.paste(img_transf, offset, img_transf)   
            img_bg.convert('CMYK') 

            print(img_bg.getpixel((0,0)))

            vsk.stroke(i+1)
            vsk.fill(i+1)

            for x in range(max_size):
                pos_x = map_range(x, 0, max_size, -final_x/2, final_x/2)
                for y in range(max_size):
                    pos_y = map_range(y, 0, max_size, -final_x/2, final_x/2)
                    p = img_bg.getpixel((x,y))[i]
                    circle_size = cmyk_radius(p, max_radius)

                    with vsk.pushMatrix():
                        vsk.rotate(angle, degrees=True)
                        #if i == 3:
                        #    print(circle_size)

                        vsk.circle(pos_x,pos_y,radius=circle_size, mode='center')
    

    
        vsk.vpype("color --layer 1  #00FFFF")
        vsk.vpype("color --layer 2  #FF00FF")
        vsk.vpype("color --layer 3  #FFFF00")
        vsk.vpype("color --layer 4  #000000")

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")


if __name__ == "__main__":
     CMYK_Halftone.display()