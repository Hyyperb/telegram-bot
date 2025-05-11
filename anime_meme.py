import requests
import io
import sys
from PIL import Image, ImageFont, ImageDraw


def get_image(rating="safe"):
    api_url = "https://api.nekosapi.com/v4/images/random"
    params = {"rating": rating}

    res = requests.get(api_url, params)
    # image_data = res.json()["items"][0]
    image_data = res.json()[0]

    # raw_image = requests.get(image_data["image_url"]).content
    raw_image = requests.get(image_data["url"]).content
    # raw_image = requests.get(api_url, params).content

    img = Image.open(io.BytesIO(raw_image))
    return img


def meme(img, top_text, bottom_text):
    draw = ImageDraw.Draw(img)
    COMIC_SANS = ImageFont.truetype("Comic.TTF", int(img.height * 0.1))
    draw.font = COMIC_SANS
    _, _, w, h = draw.textbbox((0, 0), top_text, font=COMIC_SANS)
    top_pos = ((img.width - w) / 2, img.height * 0.15 - h / 2)
    _, _, w, h = draw.textbbox((0, 0), bottom_text, font=COMIC_SANS)
    bottom_pos = ((img.width - w) / 2, img.height * 0.85 - h / 2)
    draw.text(top_pos, top_text, fill="white",
              stroke_fill="black", stroke_width=6)
    draw.text(
        bottom_pos, bottom_text, fill="white", stroke_fill="black", stroke_width=10
    )

    return img


if __name__ == "__main__":
    try:
        top_text, bottom_text = tuple(sys.argv[1:3])
        print(top_text, bottom_text)
        meme(get_image(), top_text, bottom_text).show()
    except ValueError:
        get_image().show()
