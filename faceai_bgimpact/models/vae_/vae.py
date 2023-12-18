import os
import torch
import torch.optim as optim

from tqdm import tqdm
from torchvision.utils import save_image
from pytorch_gan_metrics import get_fid
from pytorch_gan_metrics.utils import calc_and_save_stats

from faceai_bgimpact.data_processing.paths import data_folder
from faceai_bgimpact.models.abstract_model import AbstractModel
from faceai_bgimpact.models.data_loader import get_dataloader, denormalize_image
from faceai_bgimpact.models.utils import weights_init

from faceai_bgimpact.models.vae_.decoder import Decoder
from faceai_bgimpact.models.vae_.encoder import Encoder


class VAE(AbstractModel):
    """
    VAE class that inherits from our AbstractModel.

    Parameters
    ----------
    dataset_name : str
        Name of the dataset to use.
    latent_dim : int
        Dimension of the latent space.
    device : torch.device
        Device to use for training.
    """

    def __init__(self, dataset_name, latent_dim, device):
        # Initialize the abstract class
        super().__init__(dataset_name)
        self.dataset_name = dataset_name

        # VAE-specific attributes
        self.encoder = Encoder(latent_dim).to(device)
        self.decoder = Decoder(latent_dim).to(device)
        self.latent_dim = latent_dim

        # Apply the weights initialization
        self.encoder.apply(weights_init)
        self.decoder.apply(weights_init)

        self.start_epoch = 0
        self.optimizer_config = {}

    def loss_function(self, recon_x, x, mu, logvar):
        """VAE loss function."""
        # Reconstruction loss to measure how xell te model reconstructs the input
        BCE = torch.mean((recon_x - x) ** 2)  # MSE loss

        # KL divergence loss which encourage the latent space to be close to a standard normal distribution
        KLD = -0.5 * torch.mean(torch.mean(1 + logvar - mu.pow(2) - logvar.exp(), 1))

        return BCE + KLD * 0.1

    def reparameterize(self, mu, logvar):
        """Reparameterization trick to sample from N(mu, exp(logvar))."""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        z = mu + eps * std
        return z

    def train_init(self, lr, batch_size):
        """Initialize the training parameters and optimizer."""
        _, self.loader = get_dataloader(self.dataset_name, batch_size)
        self.optimizer = optim.Adam(list(self.encoder.parameters()) + list(self.decoder.parameters()), lr=lr)

    def train(self, num_epochs, lr, batch_size, device, save_interval=1, image_interval=50):
        """
        Trains the VAE model.

        Parameters
        ----------
        num_epochs : int
            Number of epochs to train for.
        lr : float
            Learning rate.
        batch_size : int
            Batch size.
        device : torch.device
            Device to use for training.
        save_interval : int
            Number of epochs to wait before saving the models. Defaults to 1.
        image_interval : int
            Number of iterations to wait before saving generated images. Defaults to 50.
        """
        # Initialize training parameters and optimizer
        self.train_init(lr, batch_size)

        # Make FID stats
        self.make_fid_stats(device)

        for epoch in range(self.start_epoch, num_epochs):
            self.encoder.train()
            self.decoder.train()
            running_loss = 0.0

            data_iter = tqdm(enumerate(self.loader), total=len(self.loader), desc=f"Epoch {epoch+1}/{num_epochs}")

            for i, imgs in data_iter:
                imgs = imgs.to(device)

                # Zero the parameter gradients
                # TODO: Why do we need to zero the gradients here?
                # We're doing it twice
                self.optimizer.zero_grad()

                loss = self.perform_train_step(imgs)

                running_loss += loss.item()

                if i % image_interval == 0:
                    iter_ = (epoch * len(self.loader)) + i
                    self.generate_images(iter_, epoch, device)

            epoch_loss = running_loss / len(self.loader)
            self.epoch_losses["train"].append(epoch_loss)

            if ((epoch + 1) % save_interval == 0) or (epoch <= 3):
                print(f"Saving checkpoint at epoch {epoch+1}...")
                self.save_checkpoint(epoch)

            # Evaluate the FID score, and log it as 'test' loss
            # FID needs at least 2048 images to compare the final average pooling features
            # C.f. https://github.com/mseitzer/pytorch-fid
            # We use 2048 + batch_size to ensure that ((2048 + batch_size) // batch_size) * batch_size > 2048
            fid_score = self.calculate_fid(2048 + batch_size, batch_size, device)
            self.epoch_losses["test"].append(fid_score)
            print(f"FID: {fid_score:.2f}")

    def perform_train_step(self, real_imgs):
        """
        One step for the training phase.

        Parameters
        ----------
        real_imgs : torch.Tensor
            Tensor of shape (batch_size, 3, 128, 128) containing the real images.
        """
        mu, logvar = self.encoder(real_imgs)
        z = self.reparameterize(mu, logvar)
        recon_imgs = self.decoder(z)

        loss = self.loss_function(recon_imgs, real_imgs, mu, logvar)

        # Backward pass and optimization

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return loss

    def make_fid_stats(self, device):
        """
        Calculate and save FID stats for the dataset.

        Parameters
        ----------
        device : torch.device
            Device to use for calculation.
        """
        # If device is CPU, ignore and skip
        if str(device) == "cpu":
            print("Skipping FID stats for CPU")
            return

        dataset_folder = f"{data_folder}/{self.dataset_name}"
        stats_path = f"{data_folder}/{self.dataset_name}_statistics.npz"

        # If the stats file already exists, skip
        if os.path.exists(stats_path):
            return

        print("Generating FID stats for the dataset...")
        calc_and_save_stats(
            dataset_folder,
            stats_path,
            batch_size=10,
            img_size=128,
            use_torch=True,
            num_workers=os.cpu_count() - 1,
        )

    def calculate_fid(self, num_images, batch_size, device):
        """
        Calculate the FID score.

        Parameters
        ----------
        num_images : int
            number of images used.
        batch_size : int
            Number of images used in a sample.
        device : torch.device
            Device to use for calculation.

        Returns
        -------
        fid_score : float
            Computed FID score.
        """
        self.encoder.eval()
        generated_images = []

        with torch.no_grad():
            for _ in range(num_images // batch_size):
                # Sample from the VAE latent space
                z_samples = torch.randn(batch_size, self.latent_dim).to(device)
                generated_images.append(self.decoder(z_samples).detach().cpu())

        self.decoder.train()
        # Concatenate the image
        generated_images = torch.cat(generated_images, dim=0)

        # Denormalized the image
        denormalized_imgs = denormalize_image(generated_images)

        stats_path = f"{data_folder}/{self.dataset_name}_statistics.npz"
        return get_fid(denormalized_imgs, stats_path)

    def generate_images(self, iter_, epoch, device, save_dir="outputs/VAE_images"):
        """
        Save generated images.

        Parameters
        ----------
        iter_ : int
            Current iteration.
        epoch : int
            Current epoch.
        device : torch.device
            Device to use for training.
        save_dir : str
            Directory to save the images to.
        """
        with torch.no_grad():
            save_folder = self.get_save_dir(save_dir)
            os.makedirs(save_folder, exist_ok=True)

            # Get first batch and get the first 64 images of it
            real_imgs = next(iter(self.loader))[:64].to(device)

            mu, logvar = self.encoder(real_imgs)
            z = self.reparameterize(mu, logvar)
            recon_imgs = self.decoder(z)

            denormalized_images = denormalize_image(recon_imgs)

            # Save the reconstructed images
            save_image(denormalized_images, f"{save_folder}/fake_{iter_}_{epoch}.png", nrow=8, normalize=False)

    def generate_one_image(self, device, save_folder, filename):
        """Generate one image and save it to the directory."""
        os.makedirs(save_folder, exist_ok=True)

        z = torch.randn(1, 3, 128, 128).to(device)
        mu, logvar = self.encoder(z)
        z_sample = self.reparameterize(mu, logvar)
        fake_image = self.decoder(z_sample).cpu()

        denormalized_image = denormalize_image(fake_image)
        save_image(denormalized_image, os.path.join(save_folder, filename), normalize=False)

    def save_checkpoint(self, epoch, save_dir="outputs/VAE_checkpoints"):
        """
        Save a checkpoint of the current state. This includes the models, optimizers, FIDs, and training params.

        Parameters
        ----------
        epoch : int
            Current epoch.
        save_dir : str
            Directory to save the checkpoint to.
        """
        save_folder = self.get_save_dir(save_dir)
        os.makedirs(save_folder, exist_ok=True)

        checkpoint_path = os.path.join(save_folder, f"checkpoint_epoch_{epoch+1}.pth")
        checkpoint = {
            "epoch": epoch + 1,  # Since we want to start from the next epoch
            "encoder_state_dict": self.encoder.state_dict(),
            "decoder_state_dict": self.decoder.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "losses": self.epoch_losses,
            "dataset_name": self.dataset_name,
            "latent_dim": self.latent_dim,
        }
        torch.save(checkpoint, checkpoint_path)
        return checkpoint_path

    @classmethod
    def from_checkpoint(cls, checkpoint_path, device):
        """
        Create a VAE instance from a checkpoint file.

        Parameters
        ----------
        checkpoint_path : str
            Path to the checkpoint file.
        device : torch.device
            Device to use for training.

        Returns
        -------
        instance : VAE
            A VAE instance with loaded state.
        """
        checkpoint = torch.load(checkpoint_path, map_location=device)

        # Extract necessary components from checkpoint
        dataset_name = checkpoint.get("dataset_name", "ffhq_raw")
        latent_dim = checkpoint.get("latent_dim", 100)

        # Create a new VAE instance
        instance = cls(dataset_name, latent_dim, device)

        # Load the state into the instance
        instance.encoder.load_state_dict(checkpoint["encoder_state_dict"])
        instance.decoder.load_state_dict(checkpoint["decoder_state_dict"])
        instance.epoch_losses = checkpoint["losses"]
        instance.start_epoch = checkpoint["epoch"]

        # Load the optimizer state
        instance.optimizer_config = checkpoint["optimizer_state_dict"]

        return instance
