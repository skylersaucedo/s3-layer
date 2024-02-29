"""
using this to upload images to endpoint
potentially working
"""

import os
import matplotlib.pyplot as plt
from PIL import Image
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from hashlib import md5
import mimetypes
import httpx
mimetypes.init()
from fastapi import Response
import json
# API_ROOT = os.environ["API_ROOT"]
# API_KEY = os.environ["API_KEY"]
# API_SECRET = os.environ["API_SECRET"]

API_ROOT = "https://api.tsi-mlops.com"
API_KEY = "cgzax4Kogqk7"
API_SECRET = "mvCRjIkRK4CK2Zhqw4rsiF0wBmD4Ir"

"""useful functions"""

def read_xml(xml_path):
    """Reads the XML file and extracts bounding box coordinates for all defects."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    defects = []
    for obj in root.findall("object"):
        name = obj.find("name").text
        xmin = int(obj.find("bndbox/xmin").text)
        ymin = int(obj.find("bndbox/ymin").text)
        xmax = int(obj.find("bndbox/xmax").text)
        ymax = int(obj.find("bndbox/ymax").text)
        defects.append((name, xmin, ymin, xmax, ymax))
    return defects

def plot_defects_on_image(image_path, xml_path):
    """QC Plots bounding boxes for all defects on the image."""
    image = Image.open(image_path)
    defects = read_xml(xml_path)

    plt.imshow(image)
    
    for name, xmin, ymin, xmax, ymax in defects:
        rect = plt.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin,
                            linewidth=1, edgecolor="r", facecolor="none")
        plt.gca().add_patch(rect)
        plt.text(xmin, ymin, name, color="r", fontsize=8, backgroundcolor="white")

    plt.title(f"Defects in {os.path.basename(image_path)}")
    plt.axis("off")  # Hide axes
    plt.show()


def grab_defect_data(image_path, xml_path):
    """grabs bounding boxes info for all defects on the image for associated xml file."""

    defect_list = []
    image = Image.open(image_path)
    defects = read_xml(xml_path)

    h, w, c = np.shape(image)
    
    for name, xmin, ymin, xmax, ymax in defects:

        xmin_n = xmin/w
        xmax_n = xmax/w
        ymin_n = ymin/h
        ymax_n = ymax/h

        img_name = os.path.basename(image_path).split('/')[-1]
        defect_list.append([img_name, h, w, c, name, xmin_n, ymin_n, xmax_n, ymax_n])

    df = pd.DataFrame(data=defect_list, columns=['image_path', 'h', 'w', 'c', 'defect', 'xmin_n', 'ymin_n','xmax_n','ymax_n'])
    return df

def upload_to_api(file_name, file_stream, file_mimetype):
    file_details_response = httpx.post(
        f"{API_ROOT}/dataset",
        files={"file": (file_name, file_stream, file_mimetype)},
        auth=(API_KEY, API_SECRET),
        timeout=600.0,
    )

    file_details = file_details_response.json() 

    if file_details_response.status_code != 200:
        print("Something happened", file_details_response.status_code)

    return file_details["dataset_object_id"]


## make sure we dont upload twice!

def get_uploaded_files():
    list_response = httpx.get(
        f"{API_ROOT}/dataset",
        auth=(os.environ["API_KEY"], os.environ["API_SECRET"]),
    )

    json_response = list_response.json()

    return json_response["files"]


def upload_tag_to_api(file_guid, tag):
    """send tag to endpoint. Tag must be string"""
    tag_details_response = httpx.post(
        f"{API_ROOT}/dataset/{file_guid}/tags",
        files={"tag": tag},
        auth=(API_KEY, API_SECRET),
        timeout=600.0,
    )

    tag_details = tag_details_response.json() 

    print('tag details: ', tag_details)

    # if tag_details.status_code != 200:
    #     print("Something happened", tag_details.status_code)
    #     return tag_details.status_code

    # else:
    #     return tag_details.status_code
    

def send_label_to_api(file_guid, label, defect_response):
    """send polygon data to api"""

    label_details_response = httpx.post(
        f"{API_ROOT}/dataset/{file_guid}/labels",
        files={"label": label, "polygon":defect_response},
        auth=(API_KEY, API_SECRET),
        timeout=600.0,
    )

    label_details_response = label_details_response.json() 

    # if label_details_response.status_code != 200:
    #     print("Something happened", label_details_response.status_code)
    #     return label_details_response.status_code

    # else:
    #     return label_details_response.status_code

    print('send label to api: ', label_details_response)

def main():
    image_cache = []

    upload_count = 0
    combined_folder = r"C:\Users\endle\Desktop\object-detection-pytorch-wandb-coco\data\combined"
    df_f = pd.DataFrame(columns=['image_path', 'h', 'w', 'c', 'defect', 'xmin_n', 'ymin_n','xmax_n','ymax_n'])

    for filename in os.listdir(combined_folder):
        print(filename)
        if filename.endswith(".bmp"):
            image_path = os.path.join(combined_folder, filename)
            xml_path = os.path.join(combined_folder, filename.replace(".bmp", ".xml"))

            if os.path.exists(xml_path): # Check if the associated .xml file exists

                #plot your defects on images here, double check overlay..its good.
                #plot_defects_on_image(image_path, xml_path)

                # defects stored as dataframe here
                df = grab_defect_data(image_path, xml_path)

                # # --- add image to API here -----
                with open(image_path, "rb") as f:
                    file_hash = md5(f.read()).hexdigest()

                    file_mimetype = mimetypes.guess_type(image_path)[0]
                    print(f"File mimetype: {file_mimetype}")
                    file_guid = upload_to_api(image_path, f, file_mimetype)
                    print(f"Uploaded {image_path} as {file_guid}")
                    image_cache.append(file_hash)
                    upload_count += 1

                    # send tag here, starting with 1st dataset

                    tag_string = "RetinaNet-POC"

                    tag_out = upload_tag_to_api(file_guid, tag_string)

                    print('tag status upload: ', tag_out)

                    ## -- Add each defect associated with each unique image
                    
                    for index, row in df_f.iterrows():
                        # cycle through each defect
                        label = row['defect']
                        xmin = float(row['xmin_n'])
                        xmax = float(row['xmax_n'])
                        ymin = float(row['ymin_n'])
                        ymax = float(row['ymax_n'])
                    
                        pac = {
                            "label": label, 
                            "polygon": [
                                {"x": xmin, "y": ymin}, 
                                {"x": xmax, "y": ymin},  
                                {"x": xmax, "y": ymax},  
                                {"x": xmin, "y": ymax}
                                ]
                            }
                        
                        packet = json.dumps(pac)

                        # packet = {
                        #     "label": label, 
                        #     "polygon": [
                        #         (xmin, ymin), 
                        #         (xmax, ymin),  
                        #         (xmax, ymax),  
                        #         (xmin, ymax)
                        #         ]
                        #     }

                        # see if this works...

                        #defect_response = Response(content=packet, media_type="application/json")

                        # send label

                        #send_label_to_api(file_guid, label, defect_response)
                        send_label_to_api(file_guid, label, packet)

                ## add json bounding box info

                # combine final dataframe
                df_f = pd.concat([df_f, df],ignore_index=True)

            else:
                print(f"Skipping {filename}: No associated .xml file found.")

    print("Defect plots generated successfully!")
    print(df_f)


if __name__ == "__main__":
    main()