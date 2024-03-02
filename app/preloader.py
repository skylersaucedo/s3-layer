import torchvision


def preload_model():
    resnet_model = torchvision.models.get_model(
        "retinanet_resnet50_fpn",
    )

    return resnet_model.eval()


if __name__ == "__main__":
    preload_model()
