import argparse
import json
import os
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm
import imageio

def parse_args():
    """Parse command-line arguments for video creation."""
    parser = argparse.ArgumentParser(description="Create a video from GAN training frames")

    parser.add_argument("--model", type=str, required=True, choices=["DCGAN", "StyleGAN"], help="Type of model")
    parser.add_argument("--dataset", type=str, required=True, help="Name of the dataset used")
    parser.add_argument("--frame-rate", type=int, default=30, help="Frame rate for the video")
    return parser.parse_args()

def load_model_config(model):
    """Load the configuration JSON for the specified model and dataset."""
    config_path = os.path.join("configs", f"default_{model.lower()}_config.json")
    with open(config_path, "r") as config_file:
        config = json.load(config_file)
    return config

def add_text_to_image(image, text):
    """Add text to an image."""
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("Nirmala.ttf", 40)
    text_position = (30, image.height - 60)  # adjust based on your image size
    draw.text(text_position, text, font=font, fill=(255, 255, 255))  # white text
    return image

def get_iter(path):
    """Gets the integer after "iter" in the path."""
    return int(path.split("iter_")[1].split("_")[0])

def create_video(image_folder, output_video, frame_rate):
    """Create a video from images using imageio."""
    images = [img for img in sorted(os.listdir(image_folder), key=get_iter) if img.endswith(".png")]
    if not images:
        raise ValueError("No images found in the specified folder.")

    output_format = output_video.split(".")[-1]

    with imageio.get_writer(output_video, fps=frame_rate, format=output_format, codec='libx264', quality=10) as writer:
        for image_name in tqdm(images):
            iter_, level, epoch, alpha = map(float, image_name[:-4].split('_')[1:]) 
            resolution = 4 * 2 ** int(level)
            img_path = os.path.join(image_folder, image_name)

            text = f"Level: {int(level)} ({resolution}x{resolution}), Epoch: {int(epoch)}, Alpha: {alpha:.2f}"
            img = Image.open(img_path)
            img_with_text = add_text_to_image(img, text)

            # Convert PIL Image to numpy array
            img_array = imageio.imread(img_path)
            writer.append_data(img_array)

if __name__ == "__main__":
    args = parse_args()
    config = load_model_config(args.model)

    image_folder = f"outputs/{args.model}_images_{args.dataset}"
    create_video(
        image_folder=image_folder,
        output_video=f"outputs/{args.model}_video_{args.dataset}.mp4",
        frame_rate=args.frame_rate,
        compress=args.compress,
    )