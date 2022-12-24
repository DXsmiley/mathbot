import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont


def hex_to_tuple(t):
	return (
		int(t[0:2], base = 16),
		int(t[2:4], base = 16),
		int(t[4:6], base = 16)
	)


def hex_to_tuple_a(t):
	return (
		int(t[0:2], base = 16),
		int(t[2:4], base = 16),
		int(t[4:6], base = 16),
		int(t[6:8], base = 16)
	)


def new_monocolour(size, colour):
	# size is a tuple of (width, height)
	return PIL.Image.new('RGBA', size, colour)


def add_border(image, size, colour):
	w, h = image.size
	base = new_monocolour((w + size * 2, h + size * 2), colour)
	base.paste(image, (size, size), image)
	return base


def paste_to_background(image, colour = (255,255,255, 255), padding = 0):
	w, h = image.size
	background = PIL.Image.new('RGBA', (w + padding * 2, h + padding * 2), colour)
	background.paste(image, (padding, padding), image)
	return background


def trim_image(im):
	bg = PIL.Image.new('RGBA', im.size, (255, 255, 255, 255))
	diff = PIL.ImageChops.difference(im, bg)
	# diff = PIL.ImageChops.add(diff, diff, 2.0, -100)
	bbox = diff.getbbox()
	if bbox:
		return im.crop(bbox)
	return im


def colour_difference(a, b):
	return sum(abs(i - j) for i, j in zip(a, b))


def replace_colour(image, original, new, threshhold = 30):
	width, height = image.size
	for y in range(height):
		for x in range(width):
			if colour_difference(image.getpixel((x, y)), original) <= threshhold:
				image.putpixel((x, y), new)


def image_invert(image):
	width, height = image.size
	for y in range(height):
		for x in range(width):
			r, g, b, a = image.getpixel((x, y))
			image.putpixel((x, y), (255 - r, 255 - g, 255 - b, a))


def image_scale_channels(image, minima, maxima):
	width, height = image.size
	for y in range(height):
		for x in range(width):
			pixel = list(image.getpixel((x, y)))
			for i in range(3):
				a = minima[i]
				b = maxima[i]
				k = pixel[i]
				pixel[i] = int(a + (b - a) * (k / 255))
			image.putpixel((x, y), tuple(pixel))


TEXT_HEIGHT = 19
TEXT_WIDTH = 300
TEXT_SCALE = 3
TEXT_FONTSIZE = 44
TEXT_FONTFACE = "fonts/roboto/Roboto-Thin.ttf"
TEXT_FONTFACE_HEADDING = "fonts/roboto/Roboto-Regular.ttf"
# TEXT_COLOUR = (32, 102, 148)
TEXT_COLOUR = (40, 40, 40)
TEXT_COLOUR_HEADDING = (240, 80, 0)
TEXT_BACKGROUND = (0, 0, 0, 0)


def textimage(txt, format = 'RGBA'):
	image = PIL.Image.new(format, (TEXT_WIDTH * TEXT_SCALE, TEXT_HEIGHT * TEXT_SCALE), TEXT_BACKGROUND)
	draw = PIL.ImageDraw.Draw(image)
	font = PIL.ImageFont.truetype(TEXT_FONTFACE, TEXT_FONTSIZE)
	draw.text((2, 0), txt, TEXT_COLOUR, font = font)
	return image.resize((TEXT_WIDTH, TEXT_HEIGHT), PIL.Image.Resampling.LANCZOS)
