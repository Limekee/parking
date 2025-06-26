import os
import time
import numpy as np
import cv2

from ultralytics import YOLO
from sender_http import *
from support import *


def get_centerbbox(box):
    x_center = int((box.xyxy[0][0] + box.xyxy[0][2]) / 2)
    y_center = int((box.xyxy[0][1] + box.xyxy[0][3]) / 2)
    center = (x_center, y_center)
    return center


def main():
    for root, dirs, files in os.walk(path):

        number_cars = {
            "Восточный регион": 0,
            "Западный регион": 0,
            "Южный регион": 0,
            "Северный регион": 0
        }

        if files:
            for file in files:
                name = file.split('.')[0]
                sectors = camera_sectors[name]

                image = cv2.imread(os.path.join(root, file))

                model = YOLO('runs/detect/training on 400 photos/weights/best.pt')

                results = model(image, verbose=False, conf=0.4)

                for sector_name, polygon_points in sectors.items():
                    polygon = np.array(polygon_points, dtype=np.int32)
                    count = 0

                    for box in results[0].boxes:
                        center = get_centerbbox(box)

                        if cv2.pointPolygonTest(polygon, center, False) >= 0:
                            count += 1

                    number_cars[sector_name] += count

            data = get_regions_status()['data']

            for region_information in data:
                value = region_information['occupied'] - number_cars[region_information['region']]
                operation = 'add' if value < 0 else 'remove'
                delta = abs(value)
                update_parking_spaces(region_information['region'], delta, operation)

            time.sleep(15)


if __name__ == '__main__':
    main()


