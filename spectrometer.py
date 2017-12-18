import sys
import math
import time
import picamera
from fractions import Fraction
from collections import OrderedDict
from PIL import Image, ImageDraw, ImageFile, ImageFont


# scan a column to determine top and bottom of area of lightness
def get_spectrum_y_bound(pix, x, middle_y, spectrum_threshold, spectrum_threshold_duration):
    c = 0
    spectrum_top = middle_y
    for y in range(middle_y, 0, -1):
        r, g, b = pix[x, y]
        brightness = r + g + b
        if brightness < spectrum_threshold:
            c = c + 1
            if c > spectrum_threshold_duration:
                break
        else:
            spectrum_top = y
            c = 0

    c = 0
    spectrum_bottom = middle_y
    for y in range(middle_y, middle_y * 2, 1):
        r, g, b = pix[x, y]
        brightness = r + g + b
        if brightness < spectrum_threshold:
            c = c + 1
            if c > spectrum_threshold_duration:
                break
        else:
            spectrum_bottom = y
            c = 0

    return spectrum_top, spectrum_bottom


# find aperture on right hand side of image along middle line
def find_aperture(pix, im, middle_x, middle_y):
    aperture_brightest = 0
    aperture_x = 0
    for x in range(middle_x, im.size[0], 1):
        r, g, b = pix[x, middle_y]
        brightness = r + g + b
        if brightness > aperture_brightest:
            aperture_brightest = brightness
            aperture_x = x

    aperture_threshold = aperture_brightest * 0.9
    aperture_x1 = aperture_x
    for x in range(aperture_x, middle_x, -1):
        r, g, b = pix[x, middle_y]
        brightness = r + g + b
        if brightness < aperture_threshold:
            aperture_x1 = x
            break

    aperture_x2 = aperture_x
    for x in range(aperture_x, im.size[0], 1):
        r, g, b = pix[x, middle_y]
        brightness = r + g + b
        if brightness < aperture_threshold:
            aperture_x2 = x
            break

    aperture_x = (aperture_x1 + aperture_x2) / 2

    spectrum_threshold_duration = 64
    aperture_y_bounds = get_spectrum_y_bound(pix, aperture_x, middle_y, aperture_threshold, spectrum_threshold_duration)
    aperture_y = (aperture_y_bounds[0] + aperture_y_bounds[1]) / 2
    aperture_height = (aperture_y_bounds[1] - aperture_y_bounds[0]) * 0.9

    return {'x': aperture_x, 'y': aperture_y, 'h': aperture_height, 'b': aperture_brightest}


# draw aperture onto image
def draw_aperture(aperture, draw):
    draw.line((aperture['x'], aperture['y'] - aperture['h'] / 2, aperture['x'], aperture['y'] + aperture['h'] / 2),
              fill="#000")


# draw scan line
def draw_scan_line(aperture, spectrum_angle, draw):
    xd = aperture['x']
    h = aperture['h'] / 2
    y0 = math.tan(spectrum_angle) * xd + aperture['y']
    draw.line((0, y0 - h, aperture['x'], aperture['y'] - h), fill="#888")
    draw.line((0, y0 + h, aperture['x'], aperture['y'] + h), fill="#888")


# return an RGB visual representation of wavelength for chart
def wavelength_to_color(lambda2):
    # Based on: http://www.efg2.com/Lab/ScienceAndEngineering/Spectra.htm
    # The foregoing is based on: http://www.midnightkite.com/color.html
    factor = 0.0

    color = [0, 0, 0]
    # thresholds = [ 380, 440, 490, 510, 580, 645, 780 ]
    #                    vio  blu  cyn  gre  yel  end
    thresholds = [380, 400, 450, 465, 520, 565, 780]
    for i in range(0, len(thresholds) - 1, 1):
        t1 = thresholds[i]
        t2 = thresholds[i + 1]
        if lambda2 < t1 or lambda2 >= t2:
            continue
        if i % 2 != 0:
            tmp = t1
            t1 = t2
            t2 = tmp
        if i < 5:
            color[i % 3] = (lambda2 - t2) / (t1 - t2)
        color[2 - i / 2] = 1.0
        factor = 1.0
        break

    # Let the intensity fall off near the vision limits
    if 380 <= lambda2 < 420:
        factor = 0.2 + 0.8 * (lambda2 - 380) / (420 - 380)
    elif 600 <= lambda2 < 780:
        factor = 0.2 + 0.8 * (780 - lambda2) / (780 - 600)
    return int(255 * color[0] * factor), int(255 * color[1] * factor), int(255 * color[2] * factor)


def main():
    name = sys.argv[1]
    shutter = int(sys.argv[2])

    camera = picamera.PiCamera()

    camera.vflip = True
    camera.framerate = Fraction(1, 6)
    camera.shutter_speed = shutter
    camera.iso = 100
    camera.exposure_mode = 'off'

    camera.awb_mode = 'off'
    camera.awb_gains = (1, 1)

    raw_filename = name + "_raw.jpg"
    time.sleep(3)
    camera.capture(raw_filename, resize=(1296, 972))

    im = Image.open(raw_filename)
    middle_y = im.size[1] / 2
    middle_x = im.size[0] / 2
    pix = im.load()
    # print im.bits, im.size, im.format

    draw = ImageDraw.Draw(im)
    spectrum_angle = 0.03

    aperture = find_aperture(pix, im, middle_x, middle_y)
    # print aperture
    draw_aperture(aperture, draw)
    draw_scan_line(aperture, spectrum_angle, draw)

    wavelength_factor = 0.892  # 1000/mm
    # wavelength_factor=0.892*2.0*600/650 # 500/mm

    xd = aperture['x']
    h = aperture['h'] / 2
    step = 1
    last_graph_y = 0
    max_result = 0
    results = OrderedDict()
    for x in range(0, xd * 7 / 8, step):
        wavelength = (xd - x) * wavelength_factor
        if wavelength < 380:
            continue
        if wavelength > 1000:
            continue

        # general efficiency curve of 1000/mm grating
        eff = (800 - (wavelength - 250)) / 800
        if eff < 0.3:
            eff = 0.3

        # notch near yellow maybe caused by camera sensitivity
        mid = 575
        width = 10
        if (mid - width) < wavelength < (mid + width):
            d = (width - abs(wavelength - mid)) / width
            eff = eff * (1 - d * 0.1)

        # up notch near 590
        mid = 588
        width = 10
        if (mid - width) < wavelength < (mid + width):
            d = (width - abs(wavelength - mid)) / width
            eff = eff * (1 + d * 0.1)

        y0 = math.tan(spectrum_angle) * (xd - x) + aperture['y']
        amplitude = 0
        ac = 0.0
        for y in range(int(y0 - h), int(y0 + h), 1):
            r, g, b = pix[x, y]
            # q=math.sqrt(r*r+b*b+g*g*1.5);
            q = r + b + g * 2
            if y < (y0 - h + 2) or y > (y0 + h - 3):
                q = q * 0.5
            amplitude = amplitude + q
            ac = ac + 1.0
        amplitude = amplitude / ac / eff
        # amplitude=1/eff
        results[str(wavelength)] = amplitude
        if amplitude > max_result:
            max_result = amplitude
        graph_y = amplitude / 50 * h
        draw.line((x - step, y0 + h - last_graph_y, x, y0 + h - graph_y), fill="#fff")
        last_graph_y = graph_y

    for wl in range(400, 1001, 50):
        x = xd - (wl / wavelength_factor)
        y0 = math.tan(spectrum_angle) * (xd - x) + aperture['y']
        draw.line((x, y0 + h + 5, x, y0 + h - 5))
        draw.text((x, y0 + h + 15), str(wl))

    exposure = max_result / (255 + 255 + 255)
    print("ideal exposure between 0.15 and 0.30")
    print("exposure=", exposure)
    if exposure < 0.15:
        print("consider increasing shutter time")
    elif exposure > 0.3:
        print("consider reducing shutter time")

    # save image with markup
    output_filename = name + "_out.jpg"
    ImageFile.MAXBLOCK = 2 ** 20
    im.save(output_filename, "JPEG", quality=80, optimize=True, progressive=True)

    # normalise results
    for wavelength in results:
        results[wavelength] = results[wavelength] / max_result

    # save csv of results
    csv_filename = name + ".csv"
    csv = open(csv_filename, 'w')
    csv.write("wavelength,amplitude\n")
    for wavelength in results:
        csv.write(wavelength)
        csv.write(",")
        csv.write("{:0.3f}".format(results[wavelength]))
        csv.write("\n")
    csv.close()

    # generate spectrum diagram
    antialias = 4
    w = 600 * antialias
    h2 = 300 * antialias

    h = h2 - 20 * antialias
    sd = Image.new('RGB', (w, h2), (255, 255, 255))
    draw = ImageDraw.Draw(sd)

    w1 = 380.0
    w2 = 780.0
    f1 = 1.0 / w1
    f2 = 1.0 / w2
    for x in range(0, w, 1):
        # Iterate across frequencies, not wavelengths
        lambda2 = 1.0 / (f1 - (float(x) / float(w) * (f1 - f2)))
        c = wavelength_to_color(lambda2)
        draw.line((x, 0, x, h), fill=c)

    pl = [(w, 0), (w, h)]
    for wavelength in results:
        wl = float(wavelength)
        x = int((wl - w1) / (w2 - w1) * w)
        # print wavelength,x
        pl.append((int(x), int((1 - results[wavelength]) * h)))
    pl.append((0, h))
    pl.append((0, 0))
    draw.polygon(pl, fill="#FFF")
    draw.polygon(pl)

    font = ImageFont.truetype("Lato-Regular.ttf", 12 * antialias)
    draw.line((0, h, w, h), fill="#000", width=antialias)

    for wl in range(400, 1001, 10):
        x = int((float(wl) - w1) / (w2 - w1) * w)
        draw.line((x, h, x, h + 3 * antialias), fill="#000", width=antialias)

    for wl in range(400, 1001, 50):
        x = int((float(wl) - w1) / (w2 - w1) * w)
        draw.line((x, h, x, h + 5 * antialias), fill="#000", width=antialias)
        wls = str(wl)
        tx = draw.textsize(wls, font=font)
        draw.text((x - tx[0] / 2, h + 5 * antialias), wls, font=font)

    # save chart
    sd = sd.resize((w / antialias, h / antialias), Image.ANTIALIAS)
    output_filename = name + "_chart.png"
    sd.save(output_filename, "PNG", quality=95, optimize=True, progressive=True)


main()
