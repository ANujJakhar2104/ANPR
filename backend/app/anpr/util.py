import cv2
import traceback
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=False, lang='en')

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

def get_car(license_plate, vehicle_track_ids):
    x1, y1, x2, y2, score, class_id = license_plate
    plate_cx = (x1 + x2) / 2.0
    plate_cy = (y1 + y2) / 2.0

    for j in range(len(vehicle_track_ids)):
        xcar1, ycar1, xcar2, ycar2, car_id = vehicle_track_ids[j]
        if xcar1 <= plate_cx <= xcar2 and ycar1 <= plate_cy <= ycar2:
            return vehicle_track_ids[j]
    return -1, -1, -1, -1, -1

import numpy as np

import numpy as np

def read_license_plate(license_plate_crop):
    if license_plate_crop is None or license_plate_crop.size == 0:
        return None, None

    try:
        h, w = license_plate_crop.shape[:2]
        
        # 1. Dynamic Scaling
        if h < 80:
            scale = 80 / h
            processed_crop = cv2.resize(license_plate_crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        elif h > 200:
            scale = 200 / h
            processed_crop = cv2.resize(license_plate_crop, None, fx=scale, fy=scale, interpolation=cv2.AREA)
        else:
            processed_crop = license_plate_crop.copy()
            
        # 2. THE ULTIMATE WATERMARK KILLER: Otsu's Binarization
        # Convert to grayscale
        gray = cv2.cvtColor(processed_crop, cv2.COLOR_BGR2GRAY)
        
        # Force the image into pure black and pure white
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # PaddleOCR requires 3 color channels, so we convert the B&W image back to BGR format
        processed_crop = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
            
        # 3. Padding
        processed_crop = cv2.copyMakeBorder(processed_crop, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        
        # Save it so you can see the magic
        cv2.imwrite("debug_binary.jpg", processed_crop)

        # Run OCR
        result = ocr.ocr(processed_crop)
        
        if not result or result[0] is None:
            return None, None

        full_text = ""
        total_score = 0.0
        valid_boxes = 0

        # Read top-to-bottom for 2-line plates
        for line in result[0]:
            if len(line) >= 2 and len(line[1]) >= 2:
                full_text += str(line[1][0]).upper()
                total_score += float(line[1][1])
                valid_boxes += 1

        if valid_boxes == 0:
            return None, None

        avg_score = total_score / valid_boxes

        clean_text = ''.join(char for char in full_text.replace(' ', '') if char.isalnum())
        
        if clean_text.startswith('IND'):
            clean_text = clean_text[3:]
        if clean_text.endswith('IND'):
            clean_text = clean_text[:-3]

        if len(clean_text) >= 3: 
            return clean_text, avg_score

        return None, None

    except Exception as e:
        print(f"OCR Error: {e}")
        return None, None


# def read_license_plate(license_plate_crop):
#     if license_plate_crop is None or license_plate_crop.size == 0:
#         return None, None

#     try:
#         # Scale and pad the image
#         processed_crop = cv2.resize(license_plate_crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
#         processed_crop = cv2.copyMakeBorder(processed_crop, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        
#         # Save it so you can inspect it in your folder
#         cv2.imwrite("debug_crop.jpg", processed_crop)

#         # Run OCR
#         result = ocr.ocr(processed_crop)
        
#         if not result or result[0] is None:
#             return None, None

#         full_text = ""
#         total_score = 0.0
#         valid_boxes = 0

#         for line in result[0]:
#             if len(line) >= 2 and len(line[1]) >= 2:
#                 full_text += str(line[1][0]).upper()
#                 total_score += float(line[1][1])
#                 valid_boxes += 1

#         if valid_boxes == 0:
#             return None, None

#         avg_score = total_score / valid_boxes

#         clean_text = ''.join(char for char in full_text.replace(' ', '') if char.isalnum())
        
#         if clean_text.startswith('IND'):
#             clean_text = clean_text[3:]
#         if clean_text.endswith('IND'):
#             clean_text = clean_text[:-3]

#         if len(clean_text) >= 3: 
#             return clean_text, avg_score

#         return None, None

#     except Exception as e:
#         # THIS PREVENTS THE 500 ERROR AND PRINTS THE REAL ISSUE!
#         print("\n" + "="*50)
#         print("🚨 PADDLEOCR CRASHED! HERE IS THE EXACT ERROR:")
#         traceback.print_exc()
#         print("="*50 + "\n")
#         return None, None

# import string
# import re
# from functools import lru_cache

# import easyocr

# from app.config import settings

# dict_char_to_int = {
#     'O': '0', 'D': '0', 'Q': '0', 'I': '1', 'L': '1', 'Z': '2', 'J': '3',
#     'A': '4', 'S': '5', 'G': '6', 'T': '7', 'B': '8', 'E': '8', 'P': '9'
# }
# dict_int_to_char = {
#     '0': 'O', '1': 'I', '2': 'Z', '3': 'J', '4': 'A', '5': 'S', '6': 'G',
#     '7': 'T', '8': 'B', '9': 'P'
# }


# @lru_cache(maxsize=1)
# def get_reader() -> "easyocr.Reader":
#     return easyocr.Reader(['en'], gpu=settings.OCR_USE_GPU)


# def write_csv(results, output_path):
#     with open(output_path, 'w') as f:
#         f.write('frame_nmr,car_id,car_bbox,license_plate_bbox,license_plate_bbox_score,license_number,license_number_score\n')
#         for frame_nmr in results.keys():
#             for car_id in results[frame_nmr].keys():
#                 if 'car' in results[frame_nmr][car_id].keys() and \
#                    'license_plate' in results[frame_nmr][car_id].keys() and \
#                    'text' in results[frame_nmr][car_id]['license_plate'].keys():
#                     f.write('{},{},{},{},{},{},{}\n'.format(
#                         frame_nmr,
#                         car_id,
#                         '[{} {} {} {}]'.format(
#                             float(results[frame_nmr][car_id]['car']['bbox'][0]),
#                             float(results[frame_nmr][car_id]['car']['bbox'][1]),
#                             float(results[frame_nmr][car_id]['car']['bbox'][2]),
#                             float(results[frame_nmr][car_id]['car']['bbox'][3])),
#                         '[{} {} {} {}]'.format(
#                             float(results[frame_nmr][car_id]['license_plate']['bbox'][0]),
#                             float(results[frame_nmr][car_id]['license_plate']['bbox'][1]),
#                             float(results[frame_nmr][car_id]['license_plate']['bbox'][2]),
#                             float(results[frame_nmr][car_id]['license_plate']['bbox'][3])),
#                         float(results[frame_nmr][car_id]['license_plate']['bbox_score']),
#                         results[frame_nmr][car_id]['license_plate']['text'],
#                         float(results[frame_nmr][car_id]['license_plate']['text_score'])
#                     ))


# def license_complies_format(text):
#     # IMPROVEMENT 2: Replaced rigid 10-char length with flexible Regex
#     # Matches common formats allowing 7 to 10 alphanumeric characters.
#     # Ex: MH12AB1234 (10), KA1A1234 (8), DL9CAE8459 (10)
#     pattern = r'^[A-Z0-9]{7,10}$'
#     if re.match(pattern, text):
#         return True
#     return False


# def format_license(text):
#     # IMPROVEMENT 3: Smart mapping. Last 4 are always digits, first 2 are always letters.
#     license_plate_ = ''
    
#     # Process prefix (State code and RTO) vs Suffix (Final 4 digits)
#     if len(text) >= 4:
#         suffix_start_idx = len(text) - 4
        
#         # 1. Map the first two characters strongly to letters
#         for i in range(min(2, suffix_start_idx)):
#             if text[i] in dict_int_to_char:
#                 license_plate_ += dict_int_to_char[text[i]]
#             else:
#                 license_plate_ += text[i]
                
#         # 2. Add the middle section as-is
#         license_plate_ += text[2:suffix_start_idx]
        
#         # 3. Map the last 4 characters strongly to numbers
#         for i in range(suffix_start_idx, len(text)):
#             if text[i] in dict_char_to_int:
#                 license_plate_ += dict_char_to_int[text[i]]
#             else:
#                 license_plate_ += text[i]
#     else:
#         # Fallback if somehow length is < 4
#         license_plate_ = text
        
#     return license_plate_


# def read_license_plate(license_plate_crop):
#     detections = get_reader().readtext(license_plate_crop)
#     if not detections:
#         return None, None
        
#     # IMPROVEMENT 4: Join all detected text to support two-line stacked plates
#     full_text = "".join([det[1] for det in detections]).upper().replace(' ', '')
    
#     if full_text.startswith('IND'):
#         full_text = full_text[3:]
        
#     # Calculate average confidence of all text blocks
#     avg_score = sum([det[2] for det in detections]) / len(detections)
    
#     if license_complies_format(full_text):
#         return format_license(full_text), avg_score
        
#     # If it fails format checks, we still return the unformatted text
#     # so you can see it in output rather than losing the detection entirely
#     return full_text, avg_score


# def get_car(license_plate, vehicle_track_ids):
#     x1, y1, x2, y2, score, class_id = license_plate
#     foundIt = False
#     car_indx = -1
#     for j in range(len(vehicle_track_ids)):
#         xcar1, ycar1, xcar2, ycar2, car_id = vehicle_track_ids[j]
#         if x1 > xcar1 and y1 > ycar1 and x2 < xcar2 and y2 < ycar2:
#             car_indx = j
#             foundIt = True
#             break
#     if foundIt:
#         return vehicle_track_ids[car_indx]
#     return -1, -1, -1, -1, -1