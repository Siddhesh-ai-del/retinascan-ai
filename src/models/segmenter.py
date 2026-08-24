import torch.nn as nn
import segmentation_models_pytorch as smp


class LesionSegmenter(nn.Module):
    def __init__(self, num_classes=4, pretrained=True):
        super().__init__()
        encoder_weights = "imagenet" if pretrained else None
        self.unet = smp.Unet(
            encoder_name="resnet18",
            encoder_weights=encoder_weights,
            in_channels=3,
            classes=num_classes,
            decoder_channels=(128, 64, 32, 16, 8),
        )

    def forward(self, x):
        return self.unet(x)
