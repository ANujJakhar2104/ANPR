import base64
import csv
import os
from typing import Optional

import cv2
import numpy as np
from scipy.interpolate import interp1d
from ultralytics import YOLO

from app.anpr.sort.sort import Sort
from app.anpr.util import get_car, read_license_plate, write_csv
from app.config import settings

VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck (COCO ids) - same as original main.py

_coco_model: Optional[YOLO] = None
_plate_model: Optional[YOLO] = None


def load_models() -> None:
    global _coco_model, _plate_model
    if _coco_model is None:
        _coco_model = YOLO(settings.COCO_MODEL_PATH)
    if _plate_model is None:
        _plate_model = YOLO(settings.PLATE_MODEL_PATH)


def _get_models() -> tuple[YOLO, YOLO]:
    if _coco_model is None or _plate_model is None:
        load_models()
    return _coco_model, _plate_model


## plate border maker

def _draw_border(img, top_left, bottom_right, color=(0, 255, 0), thickness=10,
                  line_length_x=200, line_length_y=200):
    x1, y1 = top_left
    x2, y2 = bottom_right
    cv2.line(img, (x1, y1), (x1, y1 + line_length_y), color, thickness)
    cv2.line(img, (x1, y1), (x1 + line_length_x, y1), color, thickness)
    cv2.line(img, (x1, y2), (x1, y2 - line_length_y), color, thickness)
    cv2.line(img, (x1, y2), (x1 + line_length_x, y2), color, thickness)
    cv2.line(img, (x2, y1), (x2 - line_length_x, y1), color, thickness)
    cv2.line(img, (x2, y1), (x2, y1 + line_length_y), color, thickness)
    cv2.line(img, (x2, y2), (x2, y2 - line_length_y), color, thickness)
    cv2.line(img, (x2, y2), (x2 - line_length_x, y2), color, thickness)
    return img


# single frame image detector or only image detector


def detect_image(image_path: str) -> tuple[list[dict], str]:
    coco_model, plate_model = _get_models()

    frame = cv2.imread(image_path)
    if frame is None:
        raise ValueError(f"Could not read image at {image_path}")

    detections_out = []

    vehicle_detections = coco_model(frame)[0]
    vehicles_ = []
    for detection in vehicle_detections.boxes.data.tolist():
        x1, y1, x2, y2, score, class_id = detection
        if int(class_id) in VEHICLE_CLASSES:
            vehicles_.append([x1, y1, x2, y2])

    
    if len(vehicles_) > 0:
        vehicle_ids = np.array([[*box, idx] for idx, box in enumerate(vehicles_)])
    else:
        vehicle_ids = np.empty((0, 5))

    license_plates = plate_model(frame)[0]

    for license_plate in license_plates.boxes.data.tolist():
        x1, y1, x2, y2, score, class_id = license_plate
        xcar1, ycar1, xcar2, ycar2, car_id = get_car(license_plate, vehicle_ids)

        if car_id != -1:
            license_plate_crop = frame[int(y1):int(y2), int(x1):int(x2), :]
            license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
            _, license_plate_crop_thresh = cv2.threshold(
                license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV
            )
            license_plate_text, license_plate_text_score = read_license_plate(license_plate_crop_thresh)

            _draw_border(frame, (int(xcar1), int(ycar1)), (int(xcar2), int(ycar2)),
                         (0, 255, 0), 8, line_length_x=80, line_length_y=80)
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 4)

            label = license_plate_text if license_plate_text else "UNREADABLE"
            (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            text_y = max(25, int(y1) - 10)
            cv2.rectangle(frame, (int(x1) - 4, text_y - th - 6), (int(x1) + tw + 4, text_y + baseline + 4),
                          (0, 0, 0), -1)
            cv2.putText(frame, label, (int(x1), text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

            detections_out.append({
                "car_id": int(car_id),
                "car_bbox": [float(xcar1), float(ycar1), float(xcar2), float(ycar2)],
                "license_plate_bbox": [float(x1), float(y1), float(x2), float(y2)],
                "license_plate_bbox_score": float(score),
                "license_number": license_plate_text,
                "license_number_score": float(license_plate_text_score) if license_plate_text_score else None,
            })

    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise ValueError("Failed to encode annotated image")
    annotated_b64 = base64.b64encode(buf.tobytes()).decode("ascii")

    return detections_out, annotated_b64

#video mode and this one here works for all frames of a video

def detect_video(video_path: str, csv_output_path: str) -> None:
    coco_model, plate_model = _get_models()
    mot_tracker = Sort()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video at {video_path}")

    results: dict = {}
    frame_nmr = -1
    ret = True

    while ret:
        frame_nmr += 1
        ret, frame = cap.read()
        if ret:
            results[frame_nmr] = {}
            detections = coco_model(frame)[0]
            detections_ = []
            for detection in detections.boxes.data.tolist():
                x1, y1, x2, y2, score, class_id = detection
                if int(class_id) in VEHICLE_CLASSES:
                    detections_.append([x1, y1, x2, y2, score])

            if len(detections_) > 0:
                track_ids = mot_tracker.update(np.asarray(detections_))
            else:
                track_ids = np.empty((0, 5))

            license_plates = plate_model(frame)[0]

            for license_plate in license_plates.boxes.data.tolist():
                x1, y1, x2, y2, score, class_id = license_plate
                xcar1, ycar1, xcar2, ycar2, car_id = get_car(license_plate, track_ids)

                if car_id != -1:
                    license_plate_crop = frame[int(y1):int(y2), int(x1):int(x2), :]
                    license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
                    _, license_plate_crop_thresh = cv2.threshold(
                        license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV
                    )
                    license_plate_text, license_plate_text_score = read_license_plate(license_plate_crop_thresh)

                    if license_plate_text is not None:
                        results[frame_nmr][car_id] = {
                            'car': {'bbox': [xcar1, ycar1, xcar2, ycar2]},
                            'license_plate': {
                                'bbox': [x1, y1, x2, y2],
                                'text': license_plate_text,
                                'bbox_score': score,
                                'text_score': license_plate_text_score,
                            },
                        }

    cap.release()
    write_csv(results, csv_output_path)


# interpoation and render so there is no copy and a threshold for licence plate text

def interpolate_bounding_boxes(data):
    frame_numbers = np.array([int(row['frame_nmr']) for row in data])
    car_ids = np.array([int(float(row['car_id'])) for row in data])
    car_bboxes = np.array([list(map(float, row['car_bbox'][1:-1].split())) for row in data])
    license_plate_bboxes = np.array([list(map(float, row['license_plate_bbox'][1:-1].split())) for row in data])

    interpolated_data = []
    unique_car_ids = np.unique(car_ids)
    for car_id in unique_car_ids:
        frame_numbers_ = [p['frame_nmr'] for p in data if int(float(p['car_id'])) == int(float(car_id))]

        car_mask = car_ids == car_id
        car_frame_numbers = frame_numbers[car_mask]
        car_bboxes_interpolated = []
        license_plate_bboxes_interpolated = []

        first_frame_number = car_frame_numbers[0]

        for i in range(len(car_bboxes[car_mask])):
            frame_number = car_frame_numbers[i]
            car_bbox = car_bboxes[car_mask][i]
            license_plate_bbox = license_plate_bboxes[car_mask][i]

            if i > 0:
                prev_frame_number = car_frame_numbers[i - 1]
                prev_car_bbox = car_bboxes_interpolated[-1]
                prev_license_plate_bbox = license_plate_bboxes_interpolated[-1]

                if frame_number - prev_frame_number > 1:
                    frames_gap = frame_number - prev_frame_number
                    x = np.array([prev_frame_number, frame_number])
                    x_new = np.linspace(prev_frame_number, frame_number, num=frames_gap, endpoint=False)
                    interp_func = interp1d(x, np.vstack((prev_car_bbox, car_bbox)), axis=0, kind='linear')
                    interpolated_car_bboxes = interp_func(x_new)
                    interp_func = interp1d(x, np.vstack((prev_license_plate_bbox, license_plate_bbox)), axis=0, kind='linear')
                    interpolated_license_plate_bboxes = interp_func(x_new)

                    car_bboxes_interpolated.extend(interpolated_car_bboxes[1:])
                    license_plate_bboxes_interpolated.extend(interpolated_license_plate_bboxes[1:])

            car_bboxes_interpolated.append(car_bbox)
            license_plate_bboxes_interpolated.append(license_plate_bbox)

        for i in range(len(car_bboxes_interpolated)):
            frame_number = first_frame_number + i
            row = {}
            row['frame_nmr'] = str(frame_number)
            row['car_id'] = str(car_id)
            row['car_bbox'] = ' '.join(map(str, car_bboxes_interpolated[i]))
            row['license_plate_bbox'] = ' '.join(map(str, license_plate_bboxes_interpolated[i]))

            if str(frame_number) not in frame_numbers_:
                row['license_plate_bbox_score'] = '0'
                row['license_number'] = '0'
                row['license_number_score'] = '0'
            else:
                original_row = [p for p in data if int(p['frame_nmr']) == frame_number
                                 and int(float(p['car_id'])) == int(float(car_id))][0]
                row['license_plate_bbox_score'] = original_row.get('license_plate_bbox_score', '0')
                row['license_number'] = original_row.get('license_number', '0')
                row['license_number_score'] = original_row.get('license_number_score', '0')

            interpolated_data.append(row)

    return interpolated_data


def interpolate_csv(csv_path: str, interpolated_csv_path: str) -> None:
    with open(csv_path, 'r') as file:
        reader = csv.DictReader(file)
        data = list(reader)

    if not data:
        # Nothing detected in the whole video - write an empty file with headers
        header = ['frame_nmr', 'car_id', 'car_bbox', 'license_plate_bbox',
                  'license_plate_bbox_score', 'license_number', 'license_number_score']
        with open(interpolated_csv_path, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=header)
            writer.writeheader()
        return

    interpolated_data = interpolate_bounding_boxes(data)

    header = ['frame_nmr', 'car_id', 'car_bbox', 'license_plate_bbox',
              'license_plate_bbox_score', 'license_number', 'license_number_score']
    with open(interpolated_csv_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        writer.writerows(interpolated_data)


# render video with interpolated boxes and text;

def render_video(interpolated_csv_path: str, input_video_path: str, output_video_path: str) -> None:
    import ast
    import pandas as pd

    results = pd.read_csv(interpolated_csv_path)
    if results.empty:
        # Nothing to draw - just copy the source video through untouched.
        cap = cv2.VideoCapture(input_video_path)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        ret = True
        while ret:
            ret, frame = cap.read()
            if ret:
                out.write(frame)
        cap.release()
        out.release()
        return

    cap = cv2.VideoCapture(input_video_path)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    license_plate_text_map = {}
    for car_id in np.unique(results['car_id']):
        car_df = results[results['car_id'] == car_id]
        valid_rows = car_df[~car_df['license_number'].astype(str).isin(['0', '0.0', 'nan'])]

        clean_car_id = int(car_id)
        plate_text = "UNKNOWN"

        if len(valid_rows) > 0:
            best_row = valid_rows.loc[valid_rows['license_number_score'].idxmax()]
            plate_text = str(best_row['license_number'])

        license_plate_text_map[clean_car_id] = plate_text

    frame_nmr = -1
    ret = True

    while ret:
        ret, frame = cap.read()
        frame_nmr += 1
        if ret:
            h_frame, w_frame, _ = frame.shape
            df_ = results[results['frame_nmr'] == frame_nmr]

            for row_indx in range(len(df_)):
                row = df_.iloc[row_indx]
                car_id_key = int(row['car_id'])

                car_coords = ast.literal_eval(
                    row['car_bbox'].replace('[ ', '[').replace('   ', ' ').replace('  ', ' ').replace(' ', ',')
                )
                car_x1 = max(0, int(car_coords[0]))
                car_y1 = max(0, int(car_coords[1]))
                car_x2 = min(w_frame, int(car_coords[2]))
                car_y2 = min(h_frame, int(car_coords[3]))

                _draw_border(frame, (car_x1, car_y1), (car_x2, car_y2), (0, 255, 0), 15,
                             line_length_x=150, line_length_y=150)

                lp_coords = ast.literal_eval(
                    row['license_plate_bbox'].replace('[ ', '[').replace('   ', ' ').replace('  ', ' ').replace(' ', ',')
                )
                x1 = max(0, int(lp_coords[0]))
                y1 = max(0, int(lp_coords[1]))
                x2 = min(w_frame, int(lp_coords[2]))
                y2 = min(h_frame, int(lp_coords[3]))

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 6)

                plate_text = license_plate_text_map.get(car_id_key, "UNKNOWN")
                if plate_text not in ("0", "nan"):
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.9
                    thickness = 2

                    (text_width, text_height), baseline = cv2.getTextSize(plate_text, font, font_scale, thickness)

                    text_x = x1
                    text_y = max(25, y1 - 10)

                    cv2.rectangle(frame,
                                  (text_x - 4, text_y - text_height - 6),
                                  (text_x + text_width + 4, text_y + baseline + 4),
                                  (0, 0, 0), -1)

                    cv2.putText(frame, plate_text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)

            out.write(frame)

    out.release()
    cap.release()

# runs full pipeline on a video: detect -> interpolate -> render

def run_full_video_pipeline(video_path: str, work_dir: str) -> dict:
    
    os.makedirs(work_dir, exist_ok=True)
    csv_path = os.path.join(work_dir, "detections.csv")
    interpolated_csv_path = os.path.join(work_dir, "detections_interpolated.csv")
    output_video_path = os.path.join(work_dir, "annotated.mp4")

    detect_video(video_path, csv_path)
    interpolate_csv(csv_path, interpolated_csv_path)
    render_video(interpolated_csv_path, video_path, output_video_path)

    return {
        "csv_path": csv_path,
        "interpolated_csv_path": interpolated_csv_path,
        "output_video_path": output_video_path,
    }
