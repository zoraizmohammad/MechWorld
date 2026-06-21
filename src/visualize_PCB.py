# This script was written by generative AI. It edits .jpg images to visualize a PCB.

import argparse
import os
import numpy as np
from PIL import Image

def crop_black_padding(img_np):
    """
    Detects the yellow border, removes the outer black padding, 
    and returns the cropped image.
    """
    # Yellow in RGB has high Red and Green, and low Blue.
    # We use a threshold range to safely handle JPEG compression artifacts.
    red_th = img_np[:, :, 0] > 180
    green_th = img_np[:, :, 1] > 180
    blue_th = img_np[:, :, 2] < 100
    
    yellow_mask = red_th & green_th & blue_th

    # If a yellow border is found, crop to its bounding box
    if np.any(yellow_mask):

        y_indices, x_indices = np.where(yellow_mask)
        min_y, max_y = y_indices.min(), y_indices.max()
        min_x, max_x = x_indices.min(), x_indices.max()

        remove_px_of_border = 5;
        min_y = min_y + remove_px_of_border; max_y = max_y - remove_px_of_border;
        min_x = min_x + remove_px_of_border; max_x = max_x - remove_px_of_border;

        # Crop the image to the boundary of the yellow border
        cropped_np = img_np[min_y:max_y+1, min_x:max_x+1]
        print(f"-> Yellow border detected! Stripped black padding.")
        print(f"-> Cropped from {img_np.shape[1]}x{img_np.shape[0]} down to {cropped_np.shape[1]}x{cropped_np.shape[0]}")
        return cropped_np
    else:
        print("-> Warning: No yellow border detected. Proceeding with original dimensions.")
        return img_np

def apply_pbc_padding(input_path, output_path, opacity):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.")
        return

    try:
        img = Image.open(input_path).convert("RGB")
    except Exception as e:
        print(f"Error opening image: {e}")
        return

    # Convert to numpy array
    img_np = np.array(img)
    
    # Step 1: Remove the initial black padding based on the yellow border
    img_np = crop_black_padding(img_np)
    
    # Step 2: Perform PBC processing on the clean image
    H, W, C = img_np.shape
    new_H, new_W = 2 * H, 2 * W

    # Create periodic coordinate grids via modulo arithmetic
    y_indices = (np.arange(new_H) - H // 2) % H
    x_indices = (np.arange(new_W) - W // 2) % W

    # Generate the full periodic background
    padded_np = img_np[np.ix_(y_indices, x_indices)]

    # Reduce opacity of the background sections (fades against an implicit black background)
    padded_np = (padded_np * opacity).astype(np.uint8)

    # Paste the original, full-opacity cropped image back into the center
    start_y = H // 2
    start_x = W // 2
    padded_np[start_y:start_y + H, start_x:start_x + W] = img_np

    # Convert back to PIL Image and save
    try:
        final_img = Image.fromarray(padded_np)
        final_img.save(output_path, "JPEG")
        print(f"Successfully processed image!")
        print(f"Final output size: {new_W}x{new_H}")
        print(f"Saved to: {output_path}")
    except Exception as e:
        print(f"Error saving image: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Strip outer padding via yellow border detection and apply PBC visualization."
    )
    
    parser.add_argument("input_path", type=str, help="Path to the input .jpg image")
    parser.add_argument("output_path", type=str, help="Path to save the modified .jpg image")
    parser.add_argument(
        "-o", "--opacity", 
        type=float, 
        default=0.4, 
        help="Opacity of the periodic boundary sections (0.0 to 1.0). Default is 0.4"
    )

    args = parser.parse_args()

    if not (0.0 <= args.opacity <= 1.0):
        print("Error: Opacity must be a float between 0.0 and 1.0")
    else:
        apply_pbc_padding(args.input_path, args.output_path, args.opacity)