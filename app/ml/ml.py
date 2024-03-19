import boto3
import cv2
import io
import math
import numpy as np
import os
import torch
import torchvision

from fastapi import (
    Depends,
    File,
    UploadFile,
    status,
)
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBasicCredentials
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session
from torchvision.transforms import functional as F
from typing import Annotated
from uuid import UUID

from ..auth import authenticate_user
from ..types import Prediction, InferenceResponse
from ..db.engine import get_local_session, SessionLocal
from ..db.models import MLModelObject, DatasetObject

from . import utils

resnet_model = torchvision.models.get_model(
    "retinanet_resnet50_fpn",
)


class TubesDataset(torch.utils.data.Dataset):
    def __init__(self, tags: list = None):
        super(TubesDataset, self).__init__()

        self.s3 = boto3.client("s3")
        self.imgs = self.load_files_metadata(tags=tags)
        self.labels = self.populate_labels()

    def populate_labels(self) -> list[str]:
        labels = []

        for img in self.imgs:
            img_labels = img["labels"]

            for label in img_labels:
                label = label["label"].lower()

                if label not in labels:
                    labels.append(label)

        return labels

    def load_files_metadata(self, tags: list = None) -> list[dict]:
        with SessionLocal() as session:
            files_query = select(DatasetObject).order_by("name")

            files_result = session.execute(files_query).all()

            files_list = []

            search_tags_set = frozenset(tags) if tags else {}

            for row in files_result:
                file = row[0]  # DatasetObject is in the first element of the tuple
                tags = frozenset([t[0].tag for t in file.tags(session=session)])

                if tags and len(tags.intersection(search_tags_set)) > 0:
                    continue

                files_list.append(file.as_dict(session=session))

            return files_list

    def polygon_to_tensor(self, polygon) -> list[float]:
        min_x = 1.0
        min_y = 1.0
        max_x = 0.0
        max_y = 0.0

        for point in polygon:
            print(f"Point: {point}")
            min_x = min(min_x, point["x"])
            min_y = min(min_y, point["y"])
            max_x = max(max_x, point["x"])
            max_y = max(max_y, point["y"])

        return [min_x, min_y, max_x, max_y]

    def __getitem__(self, idx) -> tuple[torch.Tensor, dict]:
        dataset_object = self.imgs[idx]

        s3_object = self.s3.get_object(
            Bucket=os.environ["DATASET_S3_BUCKET"],
            Key=dataset_object["s3_object_name"],
        )

        labels = dataset_object["labels"]
        boxes = []
        labels_list = []

        for label in labels:
            box = self.polygon_to_tensor(label["polygon"])
            boxes.append(box)

            label_text = label["label"].lower()

            label_idx = self.labels.index(label_text)
            labels_list.append(label_idx)

        target = {
            "boxes": torch.tensor(boxes),
            "labels": torch.tensor(labels_list),
            "image_id": torch.tensor(idx),
        }

        image = Image.open(s3_object["Body"])
        object_tensor = F.pil_to_tensor(image)
        object_tensor = F.convert_image_dtype(object_tensor)

        return object_tensor, target

    def __len__(self) -> int:
        return len(self.imgs)


def preload_model():
    return resnet_model.eval()


def detect_defects(image_data: cv2.typing.MatLike, model_data) -> list[Prediction]:
    image_width, image_height = image_data.shape[:2]

    device = torch.device("cpu")

    checkpoint = torch.load(model_data, map_location=device)
    resnet_model.load_state_dict(checkpoint["model"])

    CLASSES = ["scratch", "dent", "paint", "pit", "none"]

    resnet_model.eval()

    # sticking with the CPU for now
    #    model.cuda()

    img_c = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)

    img_t = img_c.transpose([2, 0, 1])

    img_t = np.expand_dims(img_t, axis=0)
    img_t = img_t / 255.0
    img_t = torch.FloatTensor(img_t)

    img_t = img_t.to(device)
    detections = resnet_model(img_t)[0]

    final_predictions = []

    for i in range(0, len(detections["boxes"])):
        confidence = detections["scores"][i]
        label_index = int(detections["labels"][i]) - 1
        box = detections["boxes"][i].detach().cpu().numpy()

        (startX, startY, endX, endY) = box.astype("int")

        # Just a friendly reminder we normalize the coordinates
        # to fit between 0 and 1 :)
        startX = startX / image_width
        startY = startY / image_height
        endX = endX / image_width
        endY = endY / image_height

        final_predictions.append(
            {
                "label": CLASSES[label_index],
                "confidence": float(confidence * 100),
                "polygon": [
                    {"left": startX, "top": startY, "begin_frame": 0, "end_frame": 0},
                    {"left": endX, "top": startY, "begin_frame": 0, "end_frame": 0},
                    {"left": endX, "top": endY, "begin_frame": 0, "end_frame": 0},
                    {"left": startX, "top": endY, "begin_frame": 0, "end_frame": 0},
                ],
            }
        )

    return final_predictions


def train_one_epoch(model, optimizer, data_loader, device, epoch, scaler=None):
    model.train()
    metric_logger = utils.MetricLogger(delimiter="  ")
    metric_logger.add_meter("lr", utils.SmoothedValue(window_size=1, fmt="{value:.6f}"))
    header = f"Epoch: [{epoch}]"

    lr_scheduler = None

    if epoch == 0:
        warmup_factor = 1.0 / 1000
        warmup_iters = min(1000, len(data_loader) - 1)

        lr_scheduler = torch.optim.lr_scheduler.LinearLR(
            optimizer, start_factor=warmup_factor, total_iters=warmup_iters
        )

    for images, targets in data_loader:
        loss_dict = model(images, targets)

        losses = sum(loss for loss in loss_dict.values())

        return False

        # reduce losses over all GPUs for logging purposes
        loss_dict_reduced = utils.reduce_dict(loss_dict)
        losses_reduced = sum(loss for loss in loss_dict_reduced.values())

        loss_value = losses_reduced.item()

        if not math.isfinite(loss_value):
            print(f"Loss is {loss_value}, stopping training")
            print(loss_dict_reduced)
            return

        optimizer.zero_grad()
        if scaler is not None:
            scaler.scale(losses).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            losses.backward()
            optimizer.step()

        if lr_scheduler is not None:
            lr_scheduler.step()


def _get_iou_types(model):
    model_without_ddp = model
    if isinstance(model, torch.nn.parallel.DistributedDataParallel):
        model_without_ddp = model.module
    iou_types = ["bbox"]
    if isinstance(model_without_ddp, torchvision.models.detection.MaskRCNN):
        iou_types.append("segm")
    if isinstance(model_without_ddp, torchvision.models.detection.KeypointRCNN):
        iou_types.append("keypoints")
    return iou_types


@torch.inference_mode()
def evaluate(model, data_loader, device):
    n_threads = torch.get_num_threads()
    # FIXME remove this and make paste_masks_in_image run on the GPU
    torch.set_num_threads(1)
    cpu_device = torch.device("cpu")
    model.eval()
    metric_logger = utils.MetricLogger(delimiter="  ")
    header = "Test:"

    coco = get_coco_api_from_dataset(data_loader.dataset)
    iou_types = _get_iou_types(model)
    coco_evaluator = CocoEvaluator(coco, iou_types)

    for images, targets in metric_logger.log_every(data_loader, 100, header):
        images = list(img.to(device) for img in images)

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        model_time = time.time()
        outputs = model(images)

        outputs = [{k: v.to(cpu_device) for k, v in t.items()} for t in outputs]
        model_time = time.time() - model_time

        res = {
            target["image_id"].item(): output
            for target, output in zip(targets, outputs)
        }
        evaluator_time = time.time()
        coco_evaluator.update(res)
        evaluator_time = time.time() - evaluator_time
        metric_logger.update(model_time=model_time, evaluator_time=evaluator_time)

    # gather the stats from all processes
    metric_logger.synchronize_between_processes()
    print("Averaged stats:", metric_logger)
    coco_evaluator.synchronize_between_processes()

    # accumulate predictions from all images
    coco_evaluator.accumulate()
    coco_evaluator.summarize()
    torch.set_num_threads(n_threads)
    return coco_evaluator


def model_inference(
    credentials: Annotated[HTTPBasicCredentials, Depends(authenticate_user)],
    session: Annotated[Session, Depends(get_local_session)],
    file_guid: UUID,
    file: Annotated[UploadFile, File(...)],
) -> InferenceResponse:
    file_query = select(MLModelObject).where(MLModelObject.id == file_guid)
    file_result = session.execute(file_query).one_or_none()

    if not file_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    model_file = file_result[0]  # ModelObject is in the first element of the tuple

    s3 = boto3.client("s3")

    s3_object = s3.get_object(
        Bucket=os.environ["MLMODEL_S3_BUCKET"],
        Key=model_file.s3_object_name,
    )

    model_data = io.BytesIO(s3_object["Body"].read())
    image_data = cv2.imdecode(np.frombuffer(file.file.read(), np.uint8), -1)

    predictions = detect_defects(image_data, model_data)

    return {
        "status": "OK",
        "predictions": predictions,
    }


def train_model(tags: list = None):
    dataset = TubesDataset(tags=tags)

    data_loader = torch.utils.data.DataLoader(
        dataset,
        batch_size=2,
        num_workers=0,
        collate_fn=utils.collate_fn,
    )

    optimizer = torch.optim.SGD(
        [p for p in resnet_model.parameters() if p.requires_grad],
        lr=0.02,
        momentum=0.9,
        weight_decay=0.0001,
        nesterov=False,
    )

    # optimizer = torch.optim.AdamW(parameters, lr=0.02, weight_decay=args.weight_decay)

    lr_scheduler = torch.optim.lr_scheduler.MultiStepLR(
        optimizer, milestones=[16, 22], gamma=0.1
    )

    # lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=26)

    resnet_model.to("cpu")

    for epoch in range(3):
        train_one_epoch(
            resnet_model,
            optimizer,
            data_loader,
            "cpu",
            epoch,
        )

        lr_scheduler.step()

        # if args.output_dir:
        #     checkpoint = {
        #         "model": model_without_ddp.state_dict(),
        #         "optimizer": optimizer.state_dict(),
        #         "lr_scheduler": lr_scheduler.state_dict(),
        #         "args": args,
        #         "epoch": epoch,
        #     }
        #     if args.amp:
        #         checkpoint["scaler"] = scaler.state_dict()

        # utils.save_on_master(
        #     checkpoint, os.path.join(args.output_dir, f"model_{epoch}.pth")
        # )
        # utils.save_on_master(
        #     checkpoint, os.path.join(args.output_dir, "checkpoint.pth")
        # )

        # evaluate after every epoch
        # evaluate(model, data_loader_test, device=device)
