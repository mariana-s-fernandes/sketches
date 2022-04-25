import numpy as np
import vpype as vp

import vsketch
from PIL import Image
from scipy import ndimage
import glob

from vpype.utils import PAGE_SIZES

# Angles for each layer of the image
CMYK_ANGLES = [15, 75, 0, 45]
CMYK_COLORS = [(0, 255, 255), (255, 0, 255), (255, 255, 0)]
# Get all images in directory
ext = ["jpg", "png"]
images = []
[images.extend(glob.glob("*." + e)) for e in ext]
IMG_PATH = "mountains.jpg"


def cmyk_radius(value, maxRadius):
    """Calculates circle radius depending on color intensity"""
    r = (255 - value) / 255 * maxRadius
    return r


def map_range(value, start1, stop1, start2, stop2):
    """Maps value from an initial range in (start1, stop1) to a final range (start2, stop2)"""
    return (value - start1) / (stop1 - start1) * (stop2 - start2) + start2


class CMYK_Halftone(vsketch.SketchClass):
    # Sketch parameters:
    page_size = vsketch.Param("a4", choices=PAGE_SIZES)
    image = vsketch.Param(IMG_PATH, choices=images)
    orient = vsketch.Param("landscape", choices=["portrait", "landscape"])
    center = vsketch.Param(True)
    num_x = vsketch.Param(100, 1)
    scale = vsketch.Param(0.8)
    use_k_channel = vsketch.Param(False)  # not working with PIL
    pen_width = vsketch.Param(0.3, unit="mm", step=0.05)
    max_radius = vsketch.Param(0.7)
    hatch_fill = vsketch.Param(True)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size("a4", landscape=(self.orient == "landscape"), center=self.center)
        vsk.penWidth(self.pen_width)

        # Gets page size
        if self.orient == "landscape":
            page_h, page_w = vp.convert_page_size("a4")
        else:
            page_w, page_h = vp.convert_page_size("a4")

        img = Image.open(self.image).convert("RGBA")
        x_pixels, y_pixels = img.size

        # Number of vertical steps
        num_y = int(np.floor(self.num_x * y_pixels / x_pixels))
        # Convert image to have (num_x, num_y) pixels
        img_transf = img.resize((self.num_x, num_y))
        # Convert image to array to be able to apply rotation
        img_array = np.array(img_transf)

        # Size for a square image that can fit any rotation of the input image
        max_size = int(np.ceil(np.sqrt(self.num_x**2 + num_y**2)))

        # Size of final image
        final_x = np.ceil(self.scale * page_w * max_size / self.num_x)

        # Max circle radius
        max_radius = int(round(self.max_radius * final_x / (2 * max_size)))

        print("Page size:", page_w, page_h)
        print("Final image size:", final_x)
        print("Pixels:", self.num_x, num_y)
        print("Max circle radius:", max_radius)

        # Append black if using K channel
        # Option not working with PIL
        if self.use_k_channel:
            CMYK_COLORS.append((0, 0, 0))

        # Loop for each color channel
        for i, _ in enumerate(CMYK_COLORS):
            angle = CMYK_ANGLES[i]

            # Set color layer
            vsk.stroke(i + 1)
            if self.hatch_fill:
                vsk.fill(i + 1)

            # Rotate image
            img_r = ndimage.rotate(img_array, angle)
            # Convert array to PIL image
            img_transf = Image.fromarray(img_r)

            # Paste rotated image in background image to ensure that all
            # image iterations have the same squared size, are centered
            # and have a white background
            img_w, img_h = img_transf.size
            offset = (round((max_size - img_w) / 2), round((max_size - img_h) / 2))

            img_bg = Image.new(
                "RGBA", (max_size, max_size), color=(255, 255, 255)
            )  # Create a white rgba background
            img_bg.paste(img_transf, offset, img_transf)
            img_bg.convert("CMYK")

            print(f"Rotated image size {i}:", img_w, img_h)
            print("Offset:", offset)

            # Loop through rotated image pixels
            for x in range(max_size):
                pos_x = map_range(x, 0, max_size, -final_x / 2, final_x / 2)
                for y in range(max_size):
                    pos_y = map_range(y, 0, max_size, -final_x / 2, final_x / 2)

                    # Get color intensity
                    p = img_bg.getpixel((x, y))[i]
                    # Circle size according to intensity
                    circle_size = cmyk_radius(p, max_radius)

                    # Rotate image and add circle to sketch
                    with vsk.pushMatrix():
                        vsk.rotate(angle, degrees=True)
                        vsk.circle(pos_x, pos_y, radius=circle_size, mode="center")

        # Define CMYK layer colors
        vsk.vpype("color --layer 1  #00FFFF")
        vsk.vpype("color --layer 2  #FF00FF")
        vsk.vpype("color --layer 3  #FFFF00")
        vsk.vpype("color --layer 4  #000000")

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")


if __name__ == "__main__":
    CMYK_Halftone.display()
