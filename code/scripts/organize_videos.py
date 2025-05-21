import os
import shutil

# Path to the Downloads folder
downloads_folder = r"C:\Users\sawyer\Downloads"

# Extensions to look for
video_extensions = (".mkv", ".mp4")

# Loop over all items in the Downloads folder
for item in os.listdir(downloads_folder):
    item_path = os.path.join(downloads_folder, item)

    # Process only files with the specified extensions
    if os.path.isfile(item_path) and item.lower().endswith(video_extensions):
        # Create a folder name by stripping the file extension
        folder_name = os.path.splitext(item)[0]
        folder_path = os.path.join(downloads_folder, folder_name)

        # Create the folder if it doesn't already exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created folder: {folder_path}")

        # Define the destination path for the file
        destination = os.path.join(folder_path, item)

        try:
            shutil.move(item_path, destination)
            print(f"Moved '{item}' to '{folder_path}'")
        except Exception as e:
            print(f"Error moving '{item}': {e}")
