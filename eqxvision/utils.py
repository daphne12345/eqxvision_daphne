import logging
import os
import warnings
from pathlib import Path
from typing import NewType, Optional

import equinox as eqx
import jax.numpy as jnp
import jax.tree_util as jtu


try:
    import torch
except ImportError:
    warnings.warn("PyTorch is required for loading Torchvision pre-trained weights.")

_TEMP_DIR = "/tmp/.eqx"
_Url = NewType("_Url", str)
MODEL_URLS = {
    "alexnet": "https://download.pytorch.org/models/alexnet-owt-7be5be79.pth",
    "convnext_tiny": "https://download.pytorch.org/models/convnext_tiny-983f1562.pth",
    "convnext_small": "https://download.pytorch.org/models/convnext_small-0c510722.pth",
    "convnext_base": "https://download.pytorch.org/models/convnext_base-6075fbad.pth",
    "convnext_large": "https://download.pytorch.org/models/convnext_large-ea097f82.pth",
    "densenet121": "https://download.pytorch.org/models/densenet121-a639ec97.pth",
    "densenet169": "https://download.pytorch.org/models/densenet169-b2777c0a.pth",
    "densenet201": "https://download.pytorch.org/models/densenet201-c1103571.pth",
    "densenet161": "https://download.pytorch.org/models/densenet161-8d451a50.pth",
    "efficientnet_b0": "https://download.pytorch.org/models/efficientnet_b0_rwightman-3dd342df.pth",
    "efficientnet_b1": "https://download.pytorch.org/models/efficientnet_b1_rwightman-533bc792.pth",
    "efficientnet_b2": "https://download.pytorch.org/models/efficientnet_b2_rwightman-bcdf34b7.pth",
    "efficientnet_b3": "https://download.pytorch.org/models/efficientnet_b3_rwightman-cf984f9c.pth",
    "efficientnet_b4": "https://download.pytorch.org/models/efficientnet_b4_rwightman-7eb33cd5.pth",
    "efficientnet_b5": "https://download.pytorch.org/models/efficientnet_b5_lukemelas-b6417697.pth",
    "efficientnet_b6": "https://download.pytorch.org/models/efficientnet_b6_lukemelas-c76e70fd.pth",
    "efficientnet_b7": "https://download.pytorch.org/models/efficientnet_b7_lukemelas-dcc49843.pth",
    "efficientnet_v2_s": "https://download.pytorch.org/models/efficientnet_v2_s-dd5fe13b.pth",
    "efficientnet_v2_m": "https://download.pytorch.org/models/efficientnet_v2_m-dc08266a.pth",
    "efficientnet_v2_l": "https://download.pytorch.org/models/efficientnet_v2_l-59c71312.pth",
    "googlenet": "https://download.pytorch.org/models/googlenet-1378be20.pth",
    "mobilenet_v2": "https://download.pytorch.org/models/mobilenet_v2-b0353104.pth",
    "mobilenet_v3_large": "https://download.pytorch.org/models/mobilenet_v3_large-8738ca79.pth",
    "mobilenet_v3_small": "https://download.pytorch.org/models/mobilenet_v3_small-047dcff4.pth",
    "resnet18": "https://download.pytorch.org/models/resnet18-5c106cde.pth",
    "resnet34": "https://download.pytorch.org/models/resnet34-333f7ec4.pth",
    "resnet50": "https://download.pytorch.org/models/resnet50-19c8e357.pth",
    "resnet101": "https://download.pytorch.org/models/resnet101-5d3b4d8f.pth",
    "resnet152": "https://download.pytorch.org/models/resnet152-b121ed2d.pth",
    "resnext50_32x4d": "https://download.pytorch.org/models/resnext50_32x4d-7cdf4587.pth",
    "resnext101_32x8d": "https://download.pytorch.org/models/resnext101_32x8d-8ba56ff5.pth",
    "shufflenetv2_x0.5": "https://download.pytorch.org/models/shufflenetv2_x0.5-f707e7126e.pth",
    "shufflenetv2_x1.0": "https://download.pytorch.org/models/shufflenetv2_x1-5666bf0f80.pth",
    "shufflenetv2_x1.5": None,
    "shufflenetv2_x2.0": None,
    "squeezenet1_0": "https://download.pytorch.org/models/squeezenet1_0-b66bff10.pth",
    "squeezenet1_1": "https://download.pytorch.org/models/squeezenet1_1-b8a52dc0.pth",
    "vit_small_patch16_224_dino": "https://dl.fbaipublicfiles.com/dino/"
    "dino_deitsmall16_pretrain/dino_deitsmall16_pretrain.pth",
    "vit_small_patch8_224_dino": "https://dl.fbaipublicfiles.com/dino/"
    "dino_deitsmall8_pretrain/dino_deitsmall8_pretrain.pth",
    "vit_base_patch16_224_dino": "https://dl.fbaipublicfiles.com/dino/"
    "dino_vitbase16_pretrain/dino_vitbase16_pretrain.pth",
    "vit_base_patch8_224_dino": "https://dl.fbaipublicfiles.com/dino/"
    "dino_vitbase8_pretrain/dino_vitbase8_pretrain.pth",
    "vgg11": "https://download.pytorch.org/models/vgg11-8a719046.pth",
    "vgg13": "https://download.pytorch.org/models/vgg13-19584684.pth",
    "vgg16": "https://download.pytorch.org/models/vgg16-397923af.pth",
    "vgg19": "https://download.pytorch.org/models/vgg19-dcbb9e9d.pth",
    "vgg11_bn": "https://download.pytorch.org/models/vgg11_bn-6002323d.pth",
    "vgg13_bn": "https://download.pytorch.org/models/vgg13_bn-abd245e5.pth",
    "vgg16_bn": "https://download.pytorch.org/models/vgg16_bn-6c64b313.pth",
    "vgg19_bn": "https://download.pytorch.org/models/vgg19_bn-c79401a0.pth",
    "wide_resnet50_2": "https://download.pytorch.org/models/wide_resnet50_2-95faca4d.pth",
    "wide_resnet101_2": "https://download.pytorch.org/models/wide_resnet101_2-32ee1156.pth",
}


def load_torch_weights(
    model: eqx.Module, filepath: Path = None, url: "_Url" = None
) -> eqx.Module:
    """Loads weights from a PyTorch serialised file.

    ???+ warning

        This method requires installation of the [`torch`](https://pypi.org/project/torch/) package.

    !!! note

        - This function assumes that Eqxvision's ordering of class
          attributes mirrors the `torchvision.models` implementation.
        - The saved checkpoint should **only** contain model parameters as keys.

    **Arguments:**

    - model: An `eqx.Module` for which the `jnp.ndarray` leaves are
        replaced by corresponding `PyTorch` weights.
    - filepath: `Path` to the downloaded `PyTorch` model file.
    - url: `URL` for the `PyTorch` model file. The file is downloaded to `/tmp/.eqx/` folder.

    **Returns:**
        The model with weights loaded from the `PyTorch` checkpoint.
    """
    if filepath is None and url is None:
        raise ValueError("Both filepath and url cannot be empty!")
    elif filepath and url:
        warnings.warn(f"Overriding `url` with with filepath: {filepath}.")
        url = None
    if url:
        global _TEMP_DIR
        filepath = os.path.join(_TEMP_DIR, os.path.basename(url))
        if os.path.exists(filepath):
            logging.info(
                f"Downloaded file exists at f{filepath}. Using the cached file!"
            )
        else:
            os.makedirs(_TEMP_DIR, exist_ok=True)
            torch.hub.download_url_to_file(url, filepath)
    if not os.path.exists(filepath):
        raise ValueError(f"filepath: {filepath} does not exist!")

    weights = torch.load(filepath, map_location="cpu")
    weights_iterator = iter(
        [
            jnp.asarray(weight.detach().numpy())
            for name, weight in weights.items()
            if "running" not in name and "num_batches" not in name
        ]
    )

    bn_s = []
    for name, weight in weights.items():
        if "running_mean" in name:
            bn_s.append(False)
            bn_s.append(jnp.asarray(weight.detach().numpy()))
        elif "running_var" in name:
            bn_s.append(jnp.asarray(weight.detach().numpy()))
    bn_iterator = iter(bn_s)

    leaves, tree_def = jtu.tree_flatten(model)

    new_leaves = []
    for leaf in leaves:
        if isinstance(leaf, jnp.ndarray) and not (
            leaf.size == 1 and isinstance(leaf.item(), bool)
        ):
            new_weights = next(weights_iterator)
            new_leaves.append(jnp.reshape(new_weights, leaf.shape))
        else:
            new_leaves.append(leaf)

    model = jtu.tree_unflatten(tree_def, new_leaves)

    def set_experimental(iter_bn, x):
        def set_values(y):
            if isinstance(y, eqx.experimental.StateIndex):
                current_val = next(iter_bn)
                if isinstance(current_val, bool):
                    eqx.experimental.set_state(y, jnp.asarray(False))
                else:
                    running_mean, running_var = current_val, next(iter_bn)
                    eqx.experimental.set_state(y, (running_mean, running_var))
            return y

        return jtu.tree_map(
            set_values, x, is_leaf=lambda _: isinstance(_, eqx.experimental.StateIndex)
        )

    model = jtu.tree_map(set_experimental, bn_iterator, model)
    return model


def _make_divisible(v: float, divisor: int, min_value: Optional[int] = None) -> int:
    """
    This function is taken from the original tf repo.
    It ensures that all layers have a channel number that is divisible by 8
    It can be seen here:
    https://github.com/tensorflow/models/blob/master/research/slim/nets/mobilenet/mobilenet.py
    """
    if min_value is None:
        min_value = divisor
    new_v = max(min_value, int(v + divisor / 2) // divisor * divisor)
    # Make sure that round down does not go down by more than 10%.
    if new_v < 0.9 * v:
        new_v += divisor
    return new_v