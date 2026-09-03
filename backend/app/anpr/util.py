import string
from functools import lru_cache

import easyocr

from app.config import settings

dict_char_to_int = {
    'O': '0', 'D': '0', 'Q': '0', 'I': '1', 'L': '1', 'Z': '2', 'J': '3',
    'A': '4', 'S': '5', 'G': '6', 'T': '7', 'B': '8', 'E': '8', 'P': '9'
}
dict_int_to_char = {
    '0': 'O', '1': 'I', '2': 'Z', '3': 'J', '4': 'A', '5': 'S', '6': 'G',
    '7': 'T', '8': 'B', '9': 'P'
}


@lru_cache(maxsize=1)
def get_reader() -> "easyocr.Reader":
    return easyocr.Reader(['en'], gpu=settings.OCR_USE_GPU)


def write_csv(results, output_path):
    with open(output_path, 'w') as f:
        f.write('frame_nmr,car_id,car_bbox,license_plate_bbox,license_plate_bbox_score,license_number,license_number_score\n')
        for frame_nmr in results.keys():
            for car_id in results[frame_nmr].keys():
                if 'car' in results[frame_nmr][car_id].keys() and \
                   'license_plate' in results[frame_nmr][car_id].keys() and \
                   'text' in results[frame_nmr][car_id]['license_plate'].keys():
                    f.write('{},{},{},{},{},{},{}\n'.format(
                        frame_nmr,
                        car_id,
                        '[{} {} {} {}]'.format(
                            float(results[frame_nmr][car_id]['car']['bbox'][0]),
                            float(results[frame_nmr][car_id]['car']['bbox'][1]),
                            float(results[frame_nmr][car_id]['car']['bbox'][2]),
                            float(results[frame_nmr][car_id]['car']['bbox'][3])),
                        '[{} {} {} {}]'.format(
                            float(results[frame_nmr][car_id]['license_plate']['bbox'][0]),
                            float(results[frame_nmr][car_id]['license_plate']['bbox'][1]),
                            float(results[frame_nmr][car_id]['license_plate']['bbox'][2]),
                            float(results[frame_nmr][car_id]['license_plate']['bbox'][3])),
                        float(results[frame_nmr][car_id]['license_plate']['bbox_score']),
                        results[frame_nmr][car_id]['license_plate']['text'],
                        float(results[frame_nmr][car_id]['license_plate']['text_score'])
                    ))


def license_complies_format(text):
    if len(text) != 10:
        return False
    if (text[0] in string.ascii_uppercase or text[0] in dict_int_to_char.keys()) and \
       (text[1] in string.ascii_uppercase or text[1] in dict_int_to_char.keys()) and \
       (text[2] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] or text[2] in dict_char_to_int.keys()) and \
       (text[3] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] or text[3] in dict_char_to_int.keys()) and \
       (text[4] in string.ascii_uppercase or text[4] in dict_int_to_char.keys()) and \
       (text[5] in string.ascii_uppercase or text[5] in dict_int_to_char.keys()) and \
       (text[6] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] or text[6] in dict_char_to_int.keys()) and \
       (text[7] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] or text[7] in dict_char_to_int.keys()) and \
       (text[8] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] or text[8] in dict_char_to_int.keys()) and \
       (text[9] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] or text[9] in dict_char_to_int.keys()):
        return True
    return False


def format_license(text):
    license_plate_ = ''
    mapping = {0: dict_int_to_char, 1: dict_int_to_char, 4: dict_int_to_char, 5: dict_int_to_char, 6: dict_char_to_int,
               2: dict_char_to_int, 3: dict_char_to_int, 7: dict_char_to_int, 8: dict_char_to_int, 9: dict_char_to_int}
    for j in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
        if text[j] in mapping[j].keys():
            license_plate_ += mapping[j][text[j]]
        else:
            license_plate_ += text[j]
    return license_plate_


def read_license_plate(license_plate_crop):
    detections = get_reader().readtext(license_plate_crop)
    for detection in detections:
        bbox, text, score = detection
        text = text.upper().replace(' ', '')
        if license_complies_format(text):
            return format_license(text), score
    return None, None


def get_car(license_plate, vehicle_track_ids):
    x1, y1, x2, y2, score, class_id = license_plate
    foundIt = False
    car_indx = -1
    for j in range(len(vehicle_track_ids)):
        xcar1, ycar1, xcar2, ycar2, car_id = vehicle_track_ids[j]
        if x1 > xcar1 and y1 > ycar1 and x2 < xcar2 and y2 < ycar2:
            car_indx = j
            foundIt = True
            break
    if foundIt:
        return vehicle_track_ids[car_indx]
    return -1, -1, -1, -1, -1
