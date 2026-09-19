import torch
import torch.nn as nn
from torchvision.models import convnext_tiny, ConvNeXt_Tiny_Weights, efficientnet_b2, EfficientNet_B2_Weights


class DRClassifier(nn.Module):
    """EfficientNet-B2 classifier (original)."""

    def __init__(self, num_classes=5, pretrained=True):
        super().__init__()
        weights = EfficientNet_B2_Weights.IMAGENET1K_V1 if pretrained else None
        self.backbone = efficientnet_b2(weights=weights)
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, 256),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        return self.backbone(x)


class DRClassifierConvNeXt(nn.Module):
    """ConvNeXt-Tiny classifier — modern ConvNet, 28M params, better feature extraction."""

    def __init__(self, num_classes=5, pretrained=True):
        super().__init__()
        weights = ConvNeXt_Tiny_Weights.IMAGENET1K_V1 if pretrained else None
        self.backbone = convnext_tiny(weights=weights)
        # ConvNeXt-Tiny classifier: AdaptiveAvgPool2d + Flatten + Linear(768, 1000)
        # Replace everything after the features
        in_features = 768  # ConvNeXt-Tiny feature dim
        self.backbone.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(1),
            nn.Dropout(p=0.3),
            nn.Linear(in_features, 512),
            nn.GELU(),
            nn.Dropout(p=0.2),
            nn.Linear(512, 256),
            nn.GELU(),
            nn.Dropout(p=0.15),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        return self.backbone(x)
