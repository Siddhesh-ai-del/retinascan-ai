import torch.nn as nn
from torchvision.models import efficientnet_b2, EfficientNet_B2_Weights


class DRClassifier(nn.Module):
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
