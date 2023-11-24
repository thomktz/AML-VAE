# train.py within the faceai_bgimpact package

import os
import json
import torch
from faceai_bgimpact.models import DCGAN, StyleGAN
from faceai_bgimpact.configs import configs

def list_checkpoints(checkpoint_dir):
    """List available checkpoints in the directory."""
    checkpoints = [f for f in os.listdir(checkpoint_dir) if f.endswith('.pth')]
    print("\nAvailable checkpoints:")
    epoch = lambda path: int(path.split("_")[1])
    for checkpoint in checkpoints:
        print(f"- Epoch {epoch(checkpoint)}: {checkpoint}")
    print()
    return int(input("Enter the epoch to resume from: "))

def find_checkpoint_path(checkpoint_dir, epoch):
    """Find the checkpoint path for a given epoch."""
    for file in os.listdir(checkpoint_dir):
        if file.startswith(f"step_{epoch}_"):
            return os.path.join(checkpoint_dir, file)
    raise FileNotFoundError(f"No checkpoint found for epoch {epoch} in {checkpoint_dir}")

def train_function(model, dataset, latent_dim, lr, dlr, glr, mlr, loss, batch_size, num_epochs, save_interval, image_interval, list_checkpoints_flag, checkpoint_path, checkpoint_epoch):
    # Load the default configuration
    config = configs[model.lower()]

    # Override specific settings with provided arguments
    if latent_dim:
        config['latent_dim'] = latent_dim
    if lr:
        config['lr'] = lr
    if dlr:
        config['dlr'] = dlr
    if glr:
        config['glr'] = glr
    if mlr:
        config['mlr'] = mlr
    if loss:
        config['loss'] = loss
    if batch_size:
        config['batch_size'] = batch_size
    if save_interval:
        config['save_interval'] = save_interval
    if image_interval:
        config['image_interval'] = image_interval

    # Determine the device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Handle the checkpoint listing
    if list_checkpoints_flag:
        checkpoint_dir = f"outputs/{model}_checkpoints_{dataset}"
        checkpoint_epoch = list_checkpoints(checkpoint_dir)

    # Find the checkpoint path if an epoch is provided
    if checkpoint_epoch is not None:
        checkpoint_path = find_checkpoint_path(checkpoint_dir, checkpoint_epoch)
    
    # Initialize the model
    if model.lower() == "dcgan":
        if checkpoint_path is None:
            model = DCGAN(
                dataset_name=dataset,
                latent_dim=config["latent_dim"],
                device=device,
            )
        else:
            model = DCGAN.from_checkpoint(
                checkpoint_path=checkpoint_path,
                device=device,
            )
        train_config = dict(
            num_epochs=config["num_epochs"],
            batch_size=config["batch_size"],
            lr=config["lr"],
            device=device,
            save_interval=config["save_interval"],
        )
    elif model.lower() == "stylegan":
        if checkpoint_path is None:
            model = StyleGAN(
                dataset_name=dataset,
                latent_dim=config["latent_dim"],
                w_dim=config["w_dim"],
                style_layers=config["style_layers"],
                device=device,
            )
        else:
            model = StyleGAN.from_checkpoint(
                dataset_name=dataset,
                checkpoint_path=checkpoint_path,
                loss=config["loss"],
                device=device,
                # TODO: remove the below arguments
                latent_dim=config["latent_dim"],
                w_dim=config["w_dim"],
                style_layers=config["style_layers"],
            )
        train_config = dict(
            dlr=config["dlr"],
            glr=config["glr"],
            mlr=config["mlr"],
            loss=config["loss"],
            batch_size=config["batch_size"],
            device=device,
            save_interval=config["save_interval"],
            image_interval=config["image_interval"],
            level_epochs={
                int(k): v
                for (k, v) in config["level_epochs"].items()
            },
        )

    else:
        raise ValueError("Invalid model type")

    model.train(**train_config)
